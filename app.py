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
    ordem_quadrantes = [
        'Alta Urgência / Alta Importância',   # vermelho
        'Baixa Urgência / Alta Importância',  # azul
        'Alta Urgência / Baixa Importância',  # amarelo
        'Baixa Urgência / Baixa Importância'  # cinza
    ]

    cores = {
        'Alta Urgência / Alta Importância': 'red',
        'Baixa Urgência / Alta Importância': 'blue',
        'Alta Urgência / Baixa Importância': 'orange',
        'Baixa Urgência / Baixa Importância': 'gray'
    }

    df['Urgência_jitter']    = df['Urgência'] + np.random.uniform(-0.05, 0.05, len(df))
    df['Importância_jitter'] = df['Importância'] + np.random.uniform(-0.05, 0.05, len(df))

    fig = go.Figure()

    # Linhas de quadrantes
    fig.add_shape(type="line", x0=5, y0=0, x1=5, y1=10.5,
                  line=dict(color="white", width=2, dash="dash"))
    fig.add_shape(type="line", x0=0, y0=5, x1=10.5, y1=5,
                  line=dict(color="white", width=2, dash="dash"))

    # Plota as tarefas, na ordem de cor desejada
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
                hovertemplate=(f"Tarefa: {row['Tarefas']}<br>"
                               f"Urgência: {row['Urgência']}<br>"
                               f"Importância: {row['Importância']}<extra></extra>"),
                showlegend=True
            ))

    # Layout com fundo transparente e fontes brancas
    fig.update_layout(
        title="Plano Cartesiano de Tarefas",
        xaxis=dict(
            title=dict(
                text="Urgência",
                font=dict(family="Arial", size=14, color="white")  # Definindo a fonte para o título
            ),
            dtick=1,
            range=[0, 10.5],
            tickfont=dict(family="Arial", size=12, color="white"),  # Definindo a fonte dos ticks
            gridcolor="rgba(255,255,255,0.2)",
            zerolinecolor="rgba(255,255,255,0.2)"
        ),
        yaxis=dict(
            title=dict(
                text="Importância",
                font=dict(family="Arial", size=14, color="white")  # Definindo a fonte para o título
            ),
            dtick=1,
            range=[0, 10.5],
            tickfont=dict(family="Arial", size=12, color="white"),  # Definindo a fonte dos ticks
            gridcolor="rgba(255,255,255,0.2)",
            zerolinecolor="rgba(255,255,255,0.2)"
        ),
        legend=dict(
            title="Clique para filtrar",
            font=dict(color="white"),
            title_font=dict(color="white")
        ),
        hoverlabel=dict(
            font_color="white",
            bgcolor="rgba(0,0,0,0.7)"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    return fig


def gerar_html_resultado(plot_html):
    return f"""
    <html>
    <head>
        <title>Resultado</title>
        <!-- Favicon -->
        <link rel="icon" type="image/png" href="/static/images/icone.png">
        <style>
            body {{
                font-family: Arial, sans-serif;
                padding: 20px;
                background-image: url("/static/images/2.png");
                background-size: cover;
                background-position: center;
                color: white;
            }}
            h2 {{
                display: flex;
                align-items: center;
            }}
            /* ícone ao lado do título */
            h2 img {{
                width: 24px;
                height: 24px;
                margin-right: 8px;
            }}
            #grafico {{
                width: 100%;
                height: 700px;
            }}
            #grafico .plotly-graph-div {{
                background: transparent !important;
            }}
            .actions {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-top: 20px;
            }}
            .btn {{
                display: inline-block;
                padding: 8px 16px;
                font-size: 14px;
                text-decoration: none;
                border: none;
                border-radius: 4px;
                background-color: #007BFF;
                color: white;
                cursor: pointer;
            }}
            .btn:hover {{
                background-color: #0069d9;
            }}
        </style>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    </head>
    <body>
        <h2><img src="/static/images/icone.png" alt="Ícone">Gráfico Gerado</h2>
        <div id="grafico">{plot_html}</div>

        <div class="actions">
            <button class="btn" onclick="downloadPlot()">⬇ Baixar Gráfico</button>
            <a href="/" class="btn">⬅ Voltar</a>
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