from flask import Flask, request, render_template
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import uuid

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return mensagem_erro("Nenhum arquivo enviado.")

    file = request.files['file']
    if file.filename == '':
        return mensagem_erro("Nome do arquivo inválido.")

    filepath = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}.xlsx")
    file.save(filepath)

    try:
        df = pd.read_excel(filepath, sheet_name=0)
    except Exception as e:
        return mensagem_erro(f"Erro ao ler o arquivo Excel: {str(e)}")

    df.columns = [col.strip().lower() for col in df.columns]

    col_map = {
        'tarefas': None,
        'urgência': None,
        'importância': None
    }

    for col in df.columns:
        for key in col_map:
            if key in col:
                col_map[key] = col

    if None in col_map.values():
        return mensagem_erro('As colunas necessárias (Tarefas, Urgência, Importância) não foram encontradas.')

    df = df[[col_map['tarefas'], col_map['urgência'], col_map['importância']]].dropna().reset_index(drop=True)
    df.columns = ['Tarefas', 'Urgência', 'Importância']
    df['ID'] = df.index + 1

    df['Quadrante'] = df.apply(classificar_quadrante, axis=1)

    fig = criar_grafico(df)
    plot_html = fig.to_html(full_html=False)

    return gerar_html_resultado(plot_html)

def classificar_quadrante(row):
    if row['Urgência'] >= 5 and row['Importância'] >= 5:
        return 'Alta Urgência / Alta Importância'
    elif row['Urgência'] >= 5:
        return 'Alta Urgência / Baixa Importância'
    elif row['Importância'] >= 5:
        return 'Baixa Urgência / Alta Importância'
    else:
        return 'Baixa Urgência / Baixa Importância'

def criar_grafico(df):
    cores = {
        'Alta Urgência / Alta Importância': 'red',
        'Alta Urgência / Baixa Importância': 'orange',
        'Baixa Urgência / Alta Importância': 'blue',
        'Baixa Urgência / Baixa Importância': 'gray'
    }

    df['Urgência_jitter'] = df['Urgência'] + np.random.uniform(-0.05, 0.05, size=len(df))
    df['Importância_jitter'] = df['Importância'] + np.random.uniform(-0.05, 0.05, size=len(df))

    fig = go.Figure()

    # Linhas dos quadrantes
    fig.add_shape(
        type="line", 
        x0=5, y0=-100, x1=5, y1=100, 
        line=dict(color="black", width=2, dash="dash")
    )
    fig.add_shape(
        type="line", 
        x0=-100, y0=5, x1=100, y1=5, 
        line=dict(color="black", width=2, dash="dash")
    )

    for _, row in df.iterrows():
        fig.add_trace(go.Scatter(
            x=[row['Urgência_jitter']],
            y=[row['Importância_jitter']],
            mode='markers',
            name=row['Tarefas'],
            marker=dict(size=12, color=cores[row['Quadrante']], line=dict(width=1, color='DarkSlateGrey')),
            hovertemplate=f"Tarefa: {row['Tarefas']}<br>Urgência: {row['Urgência']}<br>Importância: {row['Importância']}<extra></extra>",
            legendgroup=row['Tarefas'],
            showlegend=True
        ))

    for quadrante, cor in cores.items():
        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            mode='markers',
            marker=dict(size=12, color=cor),
            legendgroup=quadrante,
            showlegend=True,
            name=f"{quadrante}"
        ))

    fig.update_layout(
        title="Plano Cartesiano de Tarefas",
        xaxis=dict(title="Urgência", dtick=1, range=[0, 10.5]),
        yaxis=dict(title="Importância", dtick=1, range=[0, 10.5]),
        legend_title="Clique para filtrar",
        hoverlabel=dict(bgcolor="white", font_size=12),
        margin=dict(l=50, r=50, t=50, b=50)
    )

    return fig

def gerar_html_resultado(plot_html):
    return f"""
    <html>
    <head>
        <title>Resultado</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                padding: 20px;
                background-color: #f7f9fb;
            }}
            .voltar {{
                margin-top: 20px;
            }}
            iframe {{
                width: 100%;
                height: 700px;
                border: none;
            }}
        </style>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    </head>
    <body>
        <h2>Gráfico Gerado</h2>
        <div id="grafico">{plot_html}</div>
        <div class="voltar">
            <a href="/">⬅ Voltar</a>
        </div>
    </body>
    </html>
    """

def mensagem_erro(msg):
    return f"""
    <html>
    <head><title>Erro</title></head>
    <body>
        <h2 style='color: red;'>Erro:</h2>
        <p>{msg}</p>
        <a href="/">⬅ Voltar</a>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5050, debug=True, use_reloader=True)
