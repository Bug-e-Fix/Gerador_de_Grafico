# app.py
from flask import Flask, request, render_template
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import uuid

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # Limite de 10 MB

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    # Verifica se veio arquivo
    if 'file' not in request.files:
        return mensagem_erro("Nenhum arquivo enviado.")

    file = request.files['file']
    if file.filename == '':
        return mensagem_erro("Nome do arquivo inválido.")

    # Campos de mapeamento
    col_tarefas = request.form.get('tarefas', '').strip().lower()
    col_urgencia = request.form.get('urgencia', '').strip().lower()
    col_importancia = request.form.get('importancia', '').strip().lower()

    if not (col_tarefas and col_urgencia and col_importancia):
        return mensagem_erro("Todos os campos de mapeamento (Tarefas, Urgência e Importância) devem ser preenchidos.")

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{uuid.uuid4()}.xlsx")
    file.save(filepath)

    try:
        df = pd.read_excel(filepath, sheet_name=0)
    except Exception as e:
        return mensagem_erro(f"Erro ao ler o arquivo Excel: {str(e)}")
    finally:
        # Remove sempre, sucesso ou erro
        if os.path.exists(filepath):
            os.remove(filepath)

    # Normaliza colunas do DataFrame
    df.columns = [c.strip().lower() for c in df.columns]
    if not all(c in df.columns for c in [col_tarefas, col_urgencia, col_importancia]):
        return mensagem_erro("Uma ou mais colunas informadas não foram encontradas no arquivo.")

    # Seleciona e renomeia
    df = df[[col_tarefas, col_urgencia, col_importancia]].dropna().reset_index(drop=True)
    df.columns = ['Tarefas', 'Urgência', 'Importância']
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
    # 1) Ordem desejada dos quadrantes
    ordem_quadrantes = [
        'Alta Urgência / Alta Importância',   # vermelho
        'Baixa Urgência / Alta Importância',  # azul
        'Alta Urgência / Baixa Importância',  # amarelo (orange)
        'Baixa Urgência / Baixa Importância'  # cinza
    ]

    # 2) Dicionário de cores na mesma ordem
    cores = {
        'Alta Urgência / Alta Importância': 'red',
        'Baixa Urgência / Alta Importância': 'blue',
        'Alta Urgência / Baixa Importância': 'orange',
        'Baixa Urgência / Baixa Importância': 'gray'
    }

    # 3) Aplica jitter para visualização
    df['Urgência_jitter']     = df['Urgência'] + np.random.uniform(-0.05, 0.05, len(df))
    df['Importância_jitter']  = df['Importância'] + np.random.uniform(-0.05, 0.05, len(df))

    fig = go.Figure()

    # 4) Linhas de divisão dos quadrantes
    fig.add_shape(type="line", x0=5, y0=0,   x1=5,   y1=10.5,
                  line=dict(color="black", width=2, dash="dash"))
    fig.add_shape(type="line", x0=0, y0=5,   x1=10.5, y1=5,
                  line=dict(color="black", width=2, dash="dash"))

    # 5) Para cada quadrante, primeiro agrupo e depois ploto
    for quad in ordem_quadrantes:
        subset = df[df['Quadrante'] == quad]
        for _, row in subset.iterrows():
            fig.add_trace(go.Scatter(
                x=[row['Urgência_jitter']],
                y=[row['Importância_jitter']],
                mode='markers',
                name=row['Tarefas'],
                marker=dict(
                    size=12,
                    color=cores[quad],
                    line=dict(width=1, color='DarkSlateGrey')
                ),
                hovertemplate=(
                    f"Tarefa: {row['Tarefas']}<br>"
                    f"Urgência: {row['Urgência']}<br>"
                    f"Importância: {row['Importância']}<extra></extra>"
                ),
                showlegend=True
            ))

    # 6) (Opcional) Se você não quiser repetir a legenda de cada tarefa, basta trocar showlegend=False
    #    no trace acima e só deixar estes aqui para mostrar o “mapa de cores”:

    for quad in ordem_quadrantes:
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(size=12, color=cores[quad]),
            showlegend=True,
            name=quad
        ))

    fig.update_layout(
        title="Plano Cartesiano de Tarefas",
        xaxis=dict(title="Urgência",     dtick=1, range=[0, 10.5]),
        yaxis=dict(title="Importância", dtick=1, range=[0, 10.5]),
        legend_title="Clique para filtrar",
        hoverlabel=dict(bgcolor="white", font_size=12),
        margin=dict(l=50, r=50, t=50, b=50)
    )

    return fig



def gerar_html_resultado(plot_html):
    # Botão de download usa API do Plotly
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
            #grafico {{
                width: 100%;
                height: 700px;
            }}
            button {{
                margin-bottom: 10px;
                padding: 8px 16px;
                font-size: 14px;
                border: none;
                border-radius: 4px;
                background-color: #4CAF50;
                color: white;
                cursor: pointer;
            }}
            button:hover {{
                background-color: #45a049;
            }}
        </style>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    </head>
    <body>
        <button onclick="downloadPlot()">⬇ Baixar Gráfico</button>
        <div id="grafico">{plot_html}</div>
        <div class="voltar">
            <a href="/">⬅ Voltar</a>
        </div>
        <script>
            function downloadPlot() {{
                const gd = document.querySelector('#grafico .plotly-graph-div');
                Plotly.downloadImage(gd, {{
                    format: 'png',
                    filename: 'grafico_tarefas',
                    width: 800,
                    height: 600
                }});
            }}
        </script>
    </body>
    </html>
    """

def mensagem_erro(msg):
    return f"""
    <html>
    <head>
        <title>Erro</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                padding: 20px;
                background-color: #f7f9fb;
            }}
            .erro-container {{
                background: #fee;
                border: 1px solid #f99;
                padding: 15px;
                border-radius: 4px;
            }}
            a {{
                display: inline-block;
                margin-top: 10px;
                text-decoration: none;
                color: #333;
            }}
        </style>
    </head>
    <body>
        <div class="erro-container">
            <h2 style="color: #c00;">Erro</h2>
            <p>{msg}</p>
        </div>
        <a href="/">⬅ Voltar</a>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5050, debug=True, use_reloader=True)
