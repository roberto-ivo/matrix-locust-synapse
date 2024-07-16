import csv
import requests
import json
import time

# Define os caminhos dos arquivos
input_csv = 'users.csv'
tokens_csv = 'tokens.csv'
output_csv = 'tokens_updated_STI.csv'
failed_txt = 'failed_users.txt'

# server_name = "lapisco.ifce.edu.br"
server_name = "dv.techsmart.space"

# URL do endpoint de login
url = f"https://matrix.{server_name}/_matrix/client/v3/login"

# Cabeçalho da requisição
headers = {
    "Content-Type": "application/json"
}

# Função para logar um usuário
def login_user(username, password):
    payload = {
        "type": "m.login.password",
        "user": username,
        "password": password
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    return response

# Lê o arquivo CSV de entrada
with open(input_csv, mode='r') as infile:
    reader = csv.DictReader(infile)
    users = {row['username']: row['password'] for row in reader}

print(f"Total de usuários a serem logados: {len(users)}")

# Lê o arquivo tokens.csv existente
try:
    with open(tokens_csv, mode='r') as infile:
        reader = csv.DictReader(infile)
        tokens = {row['username']: row for row in reader}
except FileNotFoundError:
    print(f"Arquivo {tokens_csv} não encontrado.")
    tokens = {}

# Lista para armazenar os resultados
successful_users = []
failed_users = []

# Itera sobre cada usuário e tenta logá-lo
for username, password in users.items():
    if username in tokens:
        print(f"Tentando logar o usuário {username}")
        
        try:
            response = login_user(username, password)
            if response.status_code == 200:
                data = response.json()
                print(f"Usuário {username} logado com sucesso.")
                tokens[username]['access_token'] = data['access_token']
                successful_users.append(tokens[username])
            else:
                print(f"Falha ao logar o usuário {username}: {response.status_code} - {response.text}")
                failed_users.append(username)
        except Exception as e:
            print(f"Erro ao logar usuário {username}: {e}")
            failed_users.append(username)
        
        # time.sleep(10)  # Aguarda 10 segundos antes da próxima tentativa
    else:
        print(f"Usuário {username} não encontrado no arquivo {tokens_csv}.")
        failed_users.append(username)

# Escreve o arquivo CSV de saída com os tokens atualizados
with open(output_csv, mode='w', newline='') as outfile:
    fieldnames = ['username', 'user_id', 'access_token', 'sync_token']
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()
    for user in tokens.values():
        writer.writerow(user)

print(f"Usuários logados com sucesso: {len(successful_users)}")

# Escreve o arquivo de falhas
with open(failed_txt, mode='w') as f:
    for username in failed_users:
        f.write(f"{username}\n")

print(f"Usuários com falha no login: {len(failed_users)}")
print("Processo concluído.")
