import gradio as gr
import pandas as pd
import chromadb
from chromadb.utils import embedding_functions
import sqlparse
import os
from huggingface_hub import InferenceClient

## Setup and Data Ingestion
class config:
    model_id = r'all-MiniLM-L6-v2'
    collection_name = r'sql_library'
    data_path = r'./sql_data'
    ai_model = r'meta-llama/Meta-Llama-3-8B-Instruct'
    
print('Initializing ChromaDB')
chroma_client = chromadb.Client()
collection_name = config.collection_name
model_name = config.model_id

print('Initializing Huggingface client')
client = InferenceClient(token=os.environ.get('HF_TOKEN'),model=config.ai_model)

##delete if already exists
try:
    chroma_client.delete_collection(name=collection_name)
except:
    pass

collection = chroma_client.create_collection(name=collection_name)

sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)

print('Loading data from csv....')

data_path = config.data_path
data = None
dfs = []
try:
    for files in os.listdir(data_path):
        print(f'Loading file {files}')
        dfs.append(pd.read_csv(os.path.join(data_path,files)))
    data = pd.concat([dataframe for dataframe in dfs],axis=0).to_dict('records')
except FileNotFoundError:
    print(f'Data Files not found!')

if data is not None:
    ids = [str(i) for i in range(len(data))] ##primary id
    documents = [d['desc'] for d in data]

    metadatas = [{'tag':d['tag'],
                  'dialect':d['dialect'],
                  'raw_sql':d['sql']} for d in data]
    
    collection.add(
        ids =ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=sentence_transformer_ef(documents)
    )
    print(f'Succesfully indexed {len(data)} SQL queries')

def explain_selection(sql_text):
    if not sql_text:
        return 'Please give sql text'
    
    prompt = [{'role':'system','content':'You are a senior data engineer, comprehensively explain this sql query in not more than 250 words'},
        {"role": "user", "content": f'{sql_text}'}]
    try:
        response = client.chat_completion(
            messages=prompt,
            max_tokens=250,
            temperature=0.7
        )
        output = response['choices'][0]['message']['content']
        return output
    except Exception as e:
        print(f'Error talking to AI: {str(e)}')

## Search logic
def search_code(query,selected_tag,selected_dialect):
    filters = {}
    if selected_tag.lower() != 'all':
        filters['tag'] = selected_tag
    if selected_dialect.lower() != 'all':
        filters['dialect'] = selected_tag

    where_clause = None
    if len(filters) > 1:
        where_clause = {'$and':[{k:v} for k,v in filters.items()]}
    elif len(filters) == 1:
        where_clause = filters

    
    results = collection.query(
        query_texts=[query],
        n_results=2,
        where=where_clause
    )
    output_html = ""
    
    # Check if we found anything (results['documents'] is a list of lists)
    if not results['documents'] or not results['documents'][0]:
        return "<div style='color: #666; padding: 10px;'>No matches found with those filters. Try broadening your search.</div>"

    for i in range(len(results['documents'][0])):
        # Extract data from the result object
        desc = results['documents'][0][i]
        meta = results['metadatas'][0][i]
        
        # FEATURE: SQL Beautification (Makes it readable)
        formatted_sql = sqlparse.format(meta['raw_sql'], reindent=True, keyword_case='upper')
        
        # Build the HTML Card
        output_html += f"""
        <div style="border: 1px solid #e5e7eb; padding: 15px; margin-bottom: 15px; border-radius: 8px; background-color: #ffffff; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span style="font-weight: 600; color: #1f2937; font-size: 1.1em;">{desc}</span>
                <div>
                    <span style="font-size: 0.75em; background: #dbeafe; color: #1e40af; padding: 4px 8px; border-radius: 4px; margin-right: 5px;">{meta['tag']}</span>
                    <span style="font-size: 0.75em; background: #f3f4f6; color: #374151; padding: 4px 8px; border-radius: 4px; border: 1px solid #d1d5db;">{meta['dialect']}</span>
                </div>
            </div>
            <pre style="background: #1e1e1e; color: #d4d4d4; padding: 12px; border-radius: 6px; overflow-x: auto; font-family: 'Consolas', 'Monaco', monospace; margin: 0;"><code>{formatted_sql}</code></pre>
        </div>
        """
    return output_html

unique_departement = ['All'] + sorted(list(set(d['tag'] for d in data))) if data else []
unique_dialects = ['All'] + sorted(list(set(d['dialect'] for d in data))) if data else []

with gr.Blocks(title="SemantiSQL") as demo:
    
    # Header
    gr.Markdown(
        """
        # 🔎 SemantiSQL
        ### Natural Language Search for Your Database
        Don't remember the column names? Just describe what you want.
        """
    )
    
    # Search Bar & Filters
    
    with gr.Row():
        with gr.Column(scale=4):
            txt_query = gr.Textbox(label="Describe your query", placeholder="e.g. Calculate revenue from last month...")
        with gr.Column(scale=1):
            drop_tag = gr.Dropdown(choices=unique_departement, value="All", label="Department")
        with gr.Column(scale=1):
            drop_dialect = gr.Dropdown(choices=unique_dialects, value="All", label="SQL Dialect")
    
    btn_search = gr.Button("🔍 Find SQL", variant="primary")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### Results")
            out_results = gr.HTML(label="Results")

        with gr.Column(scale=1):
            gr.Markdown("### 🤖 AI Explanation")
            btn_explain = gr.Button("Explain Selected SQL")
            out_explanation = gr.Markdown("Select a query and click explain...")
            txt_code_input = gr.Textbox(label="Paste SQL here to explain", value=out_results[0],lines=5)
    
    # Bind the button click to the function
    btn_search.click(fn=search_code, inputs=[txt_query, drop_tag, drop_dialect], outputs=out_results)
    btn_explain.click(fn=explain_selection, inputs=[txt_code_input], outputs=out_explanation)
    # Bind "Enter" key on textbox to function as well
    txt_query.submit(fn=search_code, inputs=[txt_query, drop_tag, drop_dialect], outputs=out_results)

    gr.Examples(
        examples=[
            ["Calculate Monthly Recurring Revenue", "Finance", "Postgres"],
            ["List all active server instances", "DevOps", "Postgres"],
            ["Find duplicate email addresses", "Data Quality", "Postgres"]
        ],
        inputs=[txt_query,drop_tag,drop_dialect],
        label='Try these examples.'
    )

if __name__ == "__main__":
    # Launch the server
    demo.launch(theme=gr.themes.Soft())