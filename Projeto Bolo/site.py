from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = '@dsa'

# Filtro para converter a data do banco
@app.template_filter('data_br')
def formata_data(valor):
    if not valor:
        return ""
    try:
        data_obj = datetime.strptime(valor, '%Y-%m-%d')
        return data_obj.strftime('%d/%m/%Y')
    except ValueError:
        return valor

#  Auxiliares
def query_db(db_name, query, args=(), one=False, commit=False):
    """Função utilitária para reduzir repetição de código SQL"""
    with sqlite3.connect(db_name) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, args)
        if commit:
            conn.commit()
            return cursor
        rv = cursor.fetchall()
        return (rv[0] if rv else None) if one else rv

# se o usuario não estiver logado ele será redirecionado para a pagina de login
def login_obrigatorio(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_logado' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


# Rotas

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('username')
        senha = request.form.get('password')

        resultado = query_db('bancousu.db', "SELECT password FROM usuarios WHERE username = ?", (usuario,), one=True)

        if resultado and check_password_hash(resultado['password'], senha):
            session['usuario_logado'] = usuario
            return redirect(url_for('home'))

        return "<h1>Usuário ou senha incorretos.</h1>"  # Dica: Use flash messages aqui

    return render_template("login.html")


@app.route('/home')
@login_obrigatorio
def home():

    conexao = sqlite3.connect('pedidos.db')
    cursor = conexao.cursor()

    cursor.execute("SELECT * FROM encomendas WHERE status = 'Pendente'")
    pedidos_pendentes = cursor.fetchall()

    cursor.execute("SELECT * FROM encomendas WHERE status = 'Completo'")
    pedidos_completos = cursor.fetchall()

    # Buscas centralizadas
    pendentes = query_db('pedidos.db', "SELECT * FROM encomendas WHERE status = 'pendente'")
    completos = query_db('pedidos.db', "SELECT * FROM encomendas WHERE status = 'completo'")
    entregues = query_db('pedidos.db', "SELECT * FROM encomendas WHERE status = 'entregue' ORDER BY id DESC LIMIT 20")

    # Soma da Receita
    res_receita = query_db('pedidos.db', "SELECT SUM(valor) FROM encomendas WHERE status = 'entregue'", one=True)
    total_receita = res_receita[0] if res_receita and res_receita[0] else 0.0

    # Soma dos Custos (O que você gastou)
    res_custo = query_db('pedidos.db', "SELECT SUM(custo) FROM encomendas WHERE status = 'entregue'", one=True)
    total_custo = res_custo[0] if res_custo and res_custo[0] else 0.0

    # CÁLCULO DO LUCRO
    lucro_liquido = total_receita - total_custo

    return render_template("home.html",
                           usuario=session['usuario_logado'],
                           pedidos_pendentes=pendentes,
                           pedidos_completos=completos,
                           pedidos_entregues=entregues,
                           total_receita = total_receita,
                           total_custo = total_custo,
                           lucro_liquido = lucro_liquido)


@app.route('/atualizar_status/<int:id>/<novo_status>')
@login_obrigatorio
def atualizar_status(id, novo_status):
    query_db('pedidos.db', "UPDATE encomendas SET status = ? WHERE id = ?", (novo_status, id), commit=True)
    return redirect(url_for('home'))


@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        usuario = request.form.get('username')
        senha_hash = generate_password_hash(request.form.get('password'))

        try:
            query_db('bancousu.db', "INSERT INTO usuarios (username, password) VALUES (?, ?)", (usuario, senha_hash),
                     commit=True)
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "<h1>Erro: Este usuário já existe!</h1>"

    return render_template("registro.html")


@app.route('/novo_pedido', methods=['POST'])
@login_obrigatorio
def novo_pedido():
    # Pegar os dados individuais para poder calcular o custo
    tamanho = request.form.get('tamanho')
    valor_cobrado = request.form.get('valor')

    # Tabela de custos fixos
    tabela_custos = {
        '23': 10.00,
        '30': 15.50,
        '40': 20.00
    }

    # Busca o custo baseado no tamanho. Se não houver tamanho, o custo é 0.
    custo_fixo = tabela_custos.get(tamanho, 0.0)

    # Organizar os dados
    dados = (
        request.form.get('nome_cliente'),
        request.form.get('sabor'),
        tamanho,
        request.form.get('formato'),
        request.form.get('data_entrega'),
        valor_cobrado,
        custo_fixo
    )

    # 4. Inserir no banco (adicionando a coluna 'custo')
    # Certifique-se de que o VALUES tenha 7 interrogações (?)
    query_db('pedidos.db',
             "INSERT INTO encomendas (nome_cliente, sabor, tamanho_cm, formato, data_entrega, valor, custo) VALUES (?, ?, ?, ?, ?, ?, ?)",
             dados, commit=True)

    return redirect(url_for('home'))


@app.route('/logout')
def logout():
    session.pop('usuario_logado', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)