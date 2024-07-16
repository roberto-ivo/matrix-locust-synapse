import csv
import requests
import json
import time  # Importa o módulo time para gerenciar o delay

# Define os caminhos dos arquivos
input_csv = 'users.csv'
output_csv = 'tokens.csv'
failed_txt = 'failed_users.txt'

server_name = "dv.techsmart.space"

# URL do endpoint de registro
url = f"https://matrix.{server_name}/_matrix/client/v3/register"

# Cabeçalho da requisição
headers = {
    "Content-Type": "application/json"
}

# Função para registrar um usuário
def register_user(username, password):
    payload = {
        "username": username,
        "password": password,
        "auth": { "type": "m.login.dummy" }
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    return response

# Lê o arquivo CSV de entrada
with open(input_csv, mode='r') as infile:
    reader = csv.DictReader(infile)
    users = [row for row in reader]

print(f"Total de usuários a serem registrados: {len(users)}")

# Lista para armazenar os resultados
successful_users = []
failed_users = []

# Itera sobre cada usuário e tenta registrá-lo
for idx, user in enumerate(users):
    username = user['username']
    password = user['password']
    print(f"Tentando registrar o usuário {username} ({idx + 1}/{len(users)})")
    
    try:
        response = register_user(username, password)
        if response.status_code == 200:
            data = response.json()
            print(f"Usuário {username} registrado com sucesso.")
            successful_users.append({
                "username": username,
                "user_id": data['user_id'],
                "access_token": data['access_token'],
                "sync_token": ""  # Coloque o valor de sync_token, se houver
            })
        else:
            print(f"Falha ao registrar o usuário {username}: {response.status_code} - {response.text}")
            failed_users.append(username)
    except Exception as e:
        print(f"Erro ao registrar usuário {username}: {e}")
        failed_users.append(username)
    
    # time.sleep(10)  # Aguarda 10 segundos antes da próxima tentativa

# Ordena os usuários bem-sucedidos por username
successful_users.sort(key=lambda x: x['username'])

# Escreve o arquivo CSV de saída
with open(output_csv, mode='w', newline='') as outfile:
    fieldnames = ['username', 'user_id', 'access_token', 'sync_token']
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()
    for user in successful_users:
        writer.writerow(user)

print(f"Usuários registrados com sucesso: {len(successful_users)}")

# Escreve o arquivo de falhas
with open(failed_txt, mode='w') as f:
    for username in failed_users:
        f.write(f"{username}\n")

print(f"Usuários com falha no registro: {len(failed_users)}")
print("Processo concluído.")
