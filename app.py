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
    if 'file' not in request.files:
        return mensagem_erro("Nenhum arquivo enviado.")

    file = request.files['file']
    if file.filename == '':
        return mensagem_erro("Nome do arquivo inválido.")

    col_tarefas     = request.form.get('tarefas', '').strip().lower()
    col_urgencia    = request.form.get('urgencia', '').strip().lower()
    col_importancia = request.form.get('importancia', '').strip().lower()
    if not (col_tarefas and col_urgencia and col_importancia):
        return mensagem_erro("Todos os campos de mapeamento (Tarefas, Urgência e Importância) devem ser preenchidos.")

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{uuid.uuid4()}.xlsx")
    file.save(filepath)
    try:
        df = pd.read_excel(filepath, sheet_name=0)
    except Exception as e:
        return mensagem_erro(f"Erro ao ler o arquivo Excel: {e}")
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

    df.columns = [c.strip().lower() for c in df.columns]
    if not all(c in df.columns for c in [col_tarefas, col_urgencia, col_importancia]):
        return mensagem_erro("Uma ou mais colunas informadas não foram encontradas no arquivo.")

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
        'Alta Urgência / Alta Importância',
        'Baixa Urgência / Alta Importância',
        'Alta Urgência / Baixa Importância',
        'Baixa Urgência / Baixa Importância'
    ]

    cores = {
        ordem_quadrantes[0]: 'green',
        ordem_quadrantes[1]: 'blue',
        ordem_quadrantes[2]: 'yellow',
        ordem_quadrantes[3]: 'red'
    }

    verbos_acao = {
        ordem_quadrantes[0]: 'Faça',
        ordem_quadrantes[1]: 'Planeje',
        ordem_quadrantes[2]: 'Delegue',
        ordem_quadrantes[3]: 'Repense/Descarte'
    }

    # Aplica jitter para visualização
    df['x_jit'] = df['Urgência'] + np.random.uniform(-0.05, 0.05, len(df))
    df['y_jit'] = df['Importância'] + np.random.uniform(-0.05, 0.05, len(df))

    fig = go.Figure()

    # Linhas de corte no plano
    fig.add_shape(type="line", x0=5, y0=0, x1=5, y1=10,
                  line=dict(color="white", width=2, dash="dash"))
    fig.add_shape(type="line", x0=0, y0=5, x1=10, y1=5,
                  line=dict(color="white", width=2, dash="dash"))

    legenda_order = ['Faça', 'Planeje', 'Delegue', 'Repense/Descarte']
    for i, acao in enumerate(legenda_order):
        quads   = [q for q, v in verbos_acao.items() if v == acao]
        df_subs = df[df['Quadrante'].isin(quads)]
        tarefas = sorted(df_subs['Tarefas'].unique())

        # Um trace por tarefa, com legendgrouptitle para o grupo
        for j, t in enumerate(tarefas):
            df_t = df_subs[df_subs['Tarefas'] == t]
            fig.add_trace(go.Scatter(
                x=df_t['x_jit'], y=df_t['y_jit'],
                mode='markers',
                marker=dict(size=12, color=cores[quads[0]], line=dict(width=1, color='DarkSlateGrey')),
                name=t,
                legendgroup=acao,
                legendgrouptitle=dict(text=acao),
                legendrank=i*100 + j,
                showlegend=True,
                hovertemplate=(
                    "<b>%{text}</b><br>Urgência: %{x:.2f}<br>Importância: %{y:.2f}<extra></extra>"
                ),
                text=df_t['Tarefas']
            ))

    fig.update_layout(
        title="Plano Cartesiano de Tarefas",
        xaxis=dict(
            title=dict(text="Urgência", font=dict(family="Arial", size=14, color="white")),
            range=[0, 10], tick0=0, dtick=1,
            tickfont=dict(size=12, color="white"),
            gridcolor="rgba(255,255,255,0.2)", zerolinecolor="rgba(255,255,255,0.2)"
        ),
        yaxis=dict(
            title=dict(text="Importância", font=dict(family="Arial", size=14, color="white")),
            range=[0, 10], tick0=0, dtick=1,
            tickfont=dict(size=12, color="white"),
            gridcolor="rgba(255,255,255,0.2)", zerolinecolor="rgba(255,255,255,0.2)"
        ),
        legend=dict(
            title="Clique para filtrar",
            font=dict(color="white"), title_font=dict(color="white"),
            itemclick='toggleothers', itemdoubleclick='toggle'
        ),
        hoverlabel=dict(font_color="white", bgcolor="rgba(0,0,0,0.7)"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"), margin=dict(l=50, r=50, t=50, b=50)
    )

    return fig

# ... restante do código (gerar_html_resultado, mensagem_erro, main) permanece igual ...

def gerar_html_resultado(plot_html):
    return f"""
    <html>
    <head>
        <title>Resultado</title>
        <link rel="icon" href="/static/images/icone.png" type="image/png">
        <style>
            body {{
                font-family: Arial, sans-serif;
                padding: 20px;
                background-image: url("/static/images/2.png");
                background-size: cover;
                background-position: center;
                color: white;
            }}
            h2 {{ display: flex; align-items: center; }}
            h2 img {{ width: 24px; height: 24px; margin-right: 8px; }}
            #grafico {{ width: 100%; height: 700px; }}
            #grafico .plotly-graph-div {{ background: transparent !important; }}
            .actions {{
                display: flex; justify-content: space-between; margin-top: 20px;
            }}
            .btn {{
                padding: 8px 16px; border: none; border-radius: 4px;
                background-color: #007BFF; color: white; cursor: pointer;
                text-decoration: none;
            }}
            .btn:hover {{ background-color: #0069d9; }}
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
                    format: 'jpeg', filename: 'grafico_tarefas',
                    width: 800, height: 600
                }});
            }}
        </script>
    </body>
    </html>
    """


def mensagem_erro(msg):
    return f"""
    <html>
    <head><title>Erro</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; background-color: #f7f9fb; }}
        .erro-container {{ background: #fee; border: 1px solid #f99; padding: 15px; border-radius: 4px; }}
        a {{ display: inline-block; margin-top: 10px; text-decoration: none; color: #333; }}
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
