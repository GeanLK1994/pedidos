import sqlite3

DB_PATH = 'usuarios.db'

def criar_banco():
    """
    Cria as tabelas de usuários, produtos, pedidos e itens de pedido,
    e garante que o usuário Master Gean exista com role de master.
    """
    conexao = sqlite3.connect(DB_PATH)
    cursor = conexao.cursor()

    # tabela de usuários
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario  TEXT    UNIQUE NOT NULL,
            senha    TEXT    NOT NULL,
            role     TEXT    NOT NULL DEFAULT 'user'
        );
    """
    )

    # tabela de produtos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            nome       TEXT    UNIQUE NOT NULL,
            categoria  TEXT
        );
    """
    )

    # tabela de pedidos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario    TEXT    NOT NULL,
            status     TEXT    NOT NULL DEFAULT 'aberto',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """
    )

    # tabela de itens de pedido
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedido_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id   INTEGER NOT NULL,
            produto_id  INTEGER NOT NULL,
            quantity    INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(pedido_id) REFERENCES pedidos(id),
            FOREIGN KEY(produto_id) REFERENCES produtos(id)
        );
    """
    )

    conexao.commit()

    # Upsert Master Gean: tenta inserir e depois garante senha/role corretos
    cursor.execute(
        "INSERT OR IGNORE INTO usuarios (usuario, senha, role) VALUES (?, ?, ?)",
        ('Master Gean', 'master123', 'master')
    )
    cursor.execute(
        "UPDATE usuarios SET senha = ?, role = ? WHERE usuario = ?",
        ('master123', 'master', 'Master Gean')
    )
    conexao.commit()
    conexao.close()


def adicionar_usuario(usuario, senha, role='user'):
    """
    Insere um novo usuário com senha em texto e função.
    Retorna True se inserido com sucesso, False se já existe.
    """
    conexao = sqlite3.connect(DB_PATH)
    cursor = conexao.cursor()
    try:
        cursor.execute(
            'INSERT INTO usuarios (usuario, senha, role) VALUES (?, ?, ?)',
            (usuario, senha, role)
        )
        conexao.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conexao.close()


def editar_usuario(user_id, novo_usuario, nova_senha):
    """
    Atualiza nome de usuário e senha.
    """
    conexao = sqlite3.connect(DB_PATH)
    cursor = conexao.cursor()
    cursor.execute(
        'UPDATE usuarios SET usuario = ?, senha = ? WHERE id = ?',
        (novo_usuario, nova_senha, user_id)
    )
    conexao.commit()
    conexao.close()


def excluir_usuario(user_id):
    """
    Remove um usuário pelo ID.
    """
    conexao = sqlite3.connect(DB_PATH)
    cursor = conexao.cursor()
    cursor.execute(
        'DELETE FROM usuarios WHERE id = ?',
        (user_id,)
    )
    conexao.commit()
    conexao.close()


def adicionar_produto(nome, categoria=''):
    """
    Insere um novo produto com categoria.
    Retorna True se inserido, False se já existe.
    """
    conexao = sqlite3.connect(DB_PATH)
    cursor = conexao.cursor()
    try:
        cursor.execute(
            'INSERT INTO produtos (nome, categoria) VALUES (?, ?)',
            (nome, categoria)
        )
        conexao.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conexao.close()


def listar_produtos():
    """
    Retorna todos os produtos (id, nome, categoria).
    """
    conexao = sqlite3.connect(DB_PATH)
    cursor = conexao.cursor()
    cursor.execute("SELECT id, nome, categoria FROM produtos")
    produtos = cursor.fetchall()
    conexao.close()
    return produtos


def get_or_create_pedido(usuario):
    """
    Retorna pedido aberto do usuário ou cria um novo.
    """
    conexao = sqlite3.connect(DB_PATH)
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT id FROM pedidos WHERE usuario = ? AND status = 'aberto'",
        (usuario,)
    )
    row = cursor.fetchone()
    if row:
        pedido_id = row[0]
    else:
        cursor.execute(
            "INSERT INTO pedidos (usuario) VALUES (?)",
            (usuario,)
        )
        conexao.commit()
        pedido_id = cursor.lastrowid
    conexao.close()
    return pedido_id


def adicionar_item(pedido_id, produto_id, quantity=1):
    """
    Adiciona ou atualiza quantidade de um item no pedido.
    """
    conexao = sqlite3.connect(DB_PATH)
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT id, quantity FROM pedido_items WHERE pedido_id = ? AND produto_id = ?",
        (pedido_id, produto_id)
    )
    row = cursor.fetchone()
    if row:
        item_id, qtd_atual = row
        cursor.execute(
            "UPDATE pedido_items SET quantity = ? WHERE id = ?",
            (qtd_atual + quantity, item_id)
        )
    else:
        cursor.execute(
            "INSERT INTO pedido_items (pedido_id, produto_id, quantity) VALUES (?, ?, ?)",
            (pedido_id, produto_id, quantity)
        )
    conexao.commit()
    conexao.close()


def remover_item(item_id):
    """
    Remove um item do pedido.
    """
    conexao = sqlite3.connect(DB_PATH)
    cursor = conexao.cursor()
    cursor.execute('DELETE FROM pedido_items WHERE id = ?', (item_id,))
    conexao.commit()
    conexao.close()


def listar_itens(pedido_id):
    """
    Retorna lista de itens (id, nome, quantity).
    """
    conexao = sqlite3.connect(DB_PATH)
    cursor = conexao.cursor()
    cursor.execute("""
        SELECT pi.id, p.nome, pi.quantity
        FROM pedido_items pi
        JOIN produtos p ON pi.produto_id = p.id
        WHERE pi.pedido_id = ?
    """, (pedido_id,))
    itens = cursor.fetchall()
    conexao.close()
    return itens


def listar_pedidos():
    """
    Retorna os 50 pedidos mais recentes.
    """
    conexao = sqlite3.connect(DB_PATH)
    cursor = conexao.cursor()
    cursor.execute("""
        SELECT id, usuario, status, created_at
        FROM pedidos
        ORDER BY created_at DESC
        LIMIT 50
    """
    )
    pedidos = cursor.fetchall()
    conexao.close()
    return pedidos


def fechar_pedido(pedido_id):
    """
    Fecha um pedido.
    """
    conexao = sqlite3.connect(DB_PATH)
    cursor = conexao.cursor()
    cursor.execute(
        "UPDATE pedidos SET status = 'fechado' WHERE id = ?",
        (pedido_id,)
    )
    conexao.commit()
    conexao.close()
