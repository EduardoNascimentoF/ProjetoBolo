import sqlite3

def restaurar_banco():
    # Cria (ou abre) o arquivo pedidos.db
    conexao = sqlite3.connect('pedidos.db')
    cursor = conexao.cursor()

    print("Criando tabelas...")

    # 2. Tabela de Encomendas (Com a coluna status inclusa)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS encomendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_cliente TEXT NOT NULL,
        sabor TEXT NOT NULL,
        tamanho_cm INTEGER CHECK(tamanho_cm IN (23, 30, 40)),
        formato TEXT CHECK(formato IN ('Redondo', 'Quadrado')),
        valor_total DECIMAL(10, 2) NOT NULL,x
        data_entrega TEXT NOT NULL,
        status TEXT DEFAULT 'pendente'
    )
    ''')

    conexao.commit()
    conexao.close()
    print("Sucesso! O arquivo 'pedidos.db' foi restaurado na sua pasta.")

if __name__ == "__main__":
    restaurar_banco()