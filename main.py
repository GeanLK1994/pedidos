from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3

from models import (
    criar_banco,
    adicionar_usuario,
    editar_usuario,
    excluir_usuario,
    adicionar_produto,
    get_or_create_pedido,
    adicionar_item,
    remover_item,
    listar_itens,
    listar_pedidos,
    fechar_pedido,
    listar_produtos
)

app = Flask(__name__)
app.secret_key = 'chave_super_secreta'

# Inicializa o banco
criar_banco()

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')
        if not usuario or not senha:
            flash('Preencha usuário e senha.', 'warning')
            return redirect(url_for('login'))

        conexao = sqlite3.connect('usuarios.db')
        cursor = conexao.cursor()
        cursor.execute('SELECT senha, role FROM usuarios WHERE usuario = ?', (usuario,))
        row = cursor.fetchone()
        conexao.close()

        if row and row[0] == senha:
            session['usuario'] = usuario
            session['role'] = row[1]
            return redirect(url_for('dashboard'))

        flash('Usuário ou senha inválidos.', 'danger')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu com sucesso.', 'info')
    return redirect(url_for('login'))

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')
        if not usuario or not senha:
            flash('Preencha usuário e senha para se cadastrar.', 'warning')
            return redirect(url_for('cadastro'))

        adicionar_usuario(usuario, senha, role='user')
        flash('Cadastro realizado com sucesso! Faça login.', 'success')
        return redirect(url_for('login'))
    return render_template('cadastro.html')

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    pedidos = listar_pedidos()
    produtos = listar_produtos()
    return render_template('dashboard.html',
                           usuario=session['usuario'],
                           role=session['role'],
                           pedidos=pedidos,
                           produtos=produtos)

@app.route('/manage_users', methods=['GET', 'POST'])
def manage_users():
    role = session.get('role')
    if role not in ('admin', 'master'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        novo_user = request.form.get('usuario')
        nova_senha = request.form.get('senha')
        if not novo_user or not nova_senha:
            flash('Usuário e senha são obrigatórios.', 'warning')
        else:
            novo_role = request.form.get('role') if role == 'master' else 'user'
            adicionar_usuario(novo_user, nova_senha, role=novo_role)
            flash('Usuário cadastrado com sucesso.', 'success')
        return redirect(url_for('manage_users'))

    conexao = sqlite3.connect('usuarios.db')
    cursor = conexao.cursor()
    if role == 'master':
        cursor.execute('SELECT id, usuario, role FROM usuarios')
    else:
        cursor.execute("SELECT id, usuario, role FROM usuarios WHERE role='user'")
    users = cursor.fetchall()
    conexao.close()
    return render_template('manage_users.html', users=users, role=role)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'role' not in session or session['role'] != 'master':
        flash('Permissão negada.', 'warning')
        return redirect(url_for('manage_users'))

    conexao = sqlite3.connect('usuarios.db')
    cursor = conexao.cursor()
    cursor.execute('SELECT usuario FROM usuarios WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conexao.close()

    if not row or row[0] == 'Master Gean':
        flash('Este usuário não pode ser excluído.', 'warning')
    else:
        excluir_usuario(user_id)
        flash('Usuário excluído com sucesso.', 'success')
    return redirect(url_for('manage_users'))

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'role' not in session:
        return redirect(url_for('login'))
    role = session['role']

    conexao = sqlite3.connect('usuarios.db')
    cursor = conexao.cursor()
    cursor.execute('SELECT id, usuario, role FROM usuarios WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conexao.close()

    if not user or (role == 'admin' and user[2] != 'user'):
        return redirect(url_for('manage_users'))

    if request.method == 'POST':
        novo_usuario = request.form.get('usuario')
        nova_senha = request.form.get('senha')
        if not novo_usuario or not nova_senha:
            flash('Nome e senha são obrigatórios.', 'warning')
        else:
            editar_usuario(user_id, novo_usuario, nova_senha)
            flash('Usuário atualizado com sucesso.', 'success')
        return redirect(url_for('manage_users'))

    return render_template('edit_user.html', user={'id': user[0], 'usuario': user[1], 'role': user[2]}, role=role)

@app.route('/cadastro_produtos', methods=['GET', 'POST'])
def cadastro_produtos():
    role = session.get('role')
    if role not in ('admin', 'master'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        nome = request.form.get('produto_nome')
        if not nome:
            flash('Informe o nome do produto.', 'warning')
        else:
            try:
                adicionar_produto(nome)
                flash('Produto cadastrado com sucesso.', 'success')
            except:
                flash('Produto já existe.', 'danger')
        return redirect(url_for('cadastro_produtos'))

    conexao = sqlite3.connect('usuarios.db')
    cursor = conexao.cursor()
    cursor.execute('SELECT id, nome FROM produtos')
    produtos = cursor.fetchall()
    conexao.close()
    return render_template('cadastro_produtos.html', produtos=produtos, role=role)

@app.route('/remover_produto/<int:produto_id>', methods=['POST'])
def remover_produto(produto_id):
    if 'role' not in session or session['role'] not in ('admin', 'master'):
        return redirect(url_for('dashboard'))
    conexao = sqlite3.connect('usuarios.db')
    cursor = conexao.cursor()
    cursor.execute('DELETE FROM produtos WHERE id = ?', (produto_id,))
    conexao.commit()
    conexao.close()
    flash('Produto removido com sucesso.', 'success')
    return redirect(url_for('cadastro_produtos'))

@app.route('/novo_pedido', methods=['GET', 'POST'])
def novo_pedido():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    usuario = session['usuario']
    pedido_id = get_or_create_pedido(usuario)
    if request.method == 'POST':
        produto_id = request.form.get('produto_id')
        quantidade = request.form.get('quantity', type=int)
        if not produto_id:
            flash('Selecione um produto antes de adicionar.', 'warning')
        else:
            adicionar_item(pedido_id, produto_id, quantidade)
            flash('Item adicionado ao pedido.', 'success')
        return redirect(url_for('novo_pedido'))
    itens = listar_itens(pedido_id)
    conexao = sqlite3.connect('usuarios.db')
    cursor = conexao.cursor()
    cursor.execute('SELECT id, nome FROM produtos')
    produtos = cursor.fetchall()
    conexao.close()
    return render_template('novo_pedido.html', pedido_id=pedido_id, itens=itens, produtos=produtos)

@app.route('/view_pedido/<int:pedido_id>', methods=['GET', 'POST'])
def view_pedido(pedido_id):
    role = session.get('role')
    if role not in ('admin', 'master'):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        produto_id = request.form.get('produto_id')
        quantidade = request.form.get('quantity', type=int)
        if produto_id and quantidade is not None:
            adicionar_item(pedido_id, produto_id, quantidade)
            flash('Item adicionado.', 'success')
        else:
            flash('Selecione produto e quantidade.', 'warning')
        return redirect(url_for('view_pedido', pedido_id=pedido_id))
    conexao = sqlite3.connect('usuarios.db')
    cursor = conexao.cursor()
    cursor.execute('SELECT status FROM pedidos WHERE id = ?', (pedido_id,))
    status = cursor.fetchone()[0]
    cursor.execute(
        'SELECT pi.id, p.nome, pi.quantity ' 
        'FROM pedido_items pi ' 
        'JOIN produtos p ON pi.produto_id = p.id ' 
        'WHERE pi.pedido_id = ?', (pedido_id,)
    )
    itens = cursor.fetchall()
    cursor.execute('SELECT id, nome FROM produtos')
    produtos = cursor.fetchall()
    conexao.close()
    return render_template('view_pedido.html', pedido_id=pedido_id, status=status, itens=itens, produtos=produtos)

@app.route('/print_pedido/<int:pedido_id>')
def print_pedido(pedido_id):
    conexao = sqlite3.connect('usuarios.db')
    cursor = conexao.cursor()
    cursor.execute('SELECT usuario, status, created_at FROM pedidos WHERE id = ?', (pedido_id,))
    pedido = cursor.fetchone()
    if not pedido:
        conexao.close()
        flash('Pedido não encontrado.', 'danger')
        return redirect(url_for('gerenciar_pedidos'))
    usuario, status, created_at = pedido
    cursor.execute(
        'SELECT p.nome, pi.quantity '
        'FROM pedido_items pi '
        'JOIN produtos p ON pi.produto_id = p.id '
        'WHERE pi.pedido_id = ?', (pedido_id,)
    )
    itens = cursor.fetchall()
    conexao.close()
    return render_template('print_pedido.html', pedido_id=pedido_id, usuario=usuario, status=status, created_at=created_at, itens=itens)

@app.route('/remove_item/<int:item_id>', methods=['POST'])
def remove_item(item_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    role = session['role']
    conexao = sqlite3.connect('usuarios.db')
    cursor = conexao.cursor()
    cursor.execute('SELECT pedido_id FROM pedido_items WHERE id = ?', (item_id,))
    row = cursor.fetchone()
    if not row:
        conexao.close()
        flash('Item não encontrado.', 'warning')
        return redirect(url_for('dashboard'))
    pedido_id = row[0]
    cursor.execute('SELECT usuario, status FROM pedidos WHERE id = ?', (pedido_id,))
    pedido_usuario, status = cursor.fetchone()
    conexao.close()
    if role == 'user' and (pedido_usuario != session['usuario'] or status != 'aberto'):
        flash('Não autorizado.', 'danger')
        return redirect(url_for('novo_pedido'))
    remover_item(item_id)
    flash('Item removido.', 'success')
    return redirect(url_for('novo_pedido')) if role == 'user' else redirect(url_for('view_pedido', pedido_id=pedido_id))

@app.route('/gerenciar_pedidos')
def gerenciar_pedidos():
    role = session.get('role')
    if role not in ('admin', 'master'):
        return redirect(url_for('dashboard'))
    pedidos = listar_pedidos()
    return render_template('gerenciar_pedidos.html', pedidos=pedidos)

@app.route('/fechar_pedido/<int:pedido_id>', methods=['POST'], endpoint='fechar_pedido')
def fechar_pedido_route(pedido_id):
    role = session.get('role')
    if role not in ('admin', 'master'):
        return redirect(url_for('dashboard'))
    fechar_pedido(pedido_id)
    flash('Pedido fechado.', 'info')
    return redirect(url_for('gerenciar_pedidos'))

if __name__ == '__main__':
    app.run(debug=True)
