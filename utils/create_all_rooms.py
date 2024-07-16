import json
import logging
import csv
import requests

# Configuração do logging
logging.basicConfig(level=logging.DEBUG)

# URL do servidor Matrix
MATRIX_SERVER = "https://matrix.dv.techsmart.space"

# Função para carregar usuários de um arquivo CSV
def load_users(file_path):
    users = []
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            users.append({
                'username': row['username'],
                'password': row['password']
            })
    return users

# Função para autenticar o usuário e obter o token de acesso
def authenticate_user(server_url, username, password):
    url = f"{server_url}/_matrix/client/v3/login"
    payload = {
        "type": "m.login.password",
        "user": username,
        "password": password
    }
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        response_data = response.json()
        logging.info(f"User '{username}' authenticated successfully.")
        return response_data['access_token']
    else:
        logging.error(f"Failed to authenticate user '{username}': {response.status_code} {response.reason}")
        logging.debug(f"Error response details: {response.text}")
        return None

# Função para criar uma sala
def create_room(server_url, access_token, room_name, user_ids):
    url = f"{server_url}/_matrix/client/v3/createRoom"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": room_name,
        "invite": user_ids
    }
    response = requests.post(url, headers=headers, json=payload)
    
    logging.debug(f"Raw response: {response.text}")
    if response.status_code == 200:
        response_data = response.json()
        logging.info(f"Room '{room_name}' created successfully with ID {response_data.get('room_id')}")
        return response_data.get('room_id')
    else:
        logging.error(f"Failed to create room '{room_name}': {response.status_code} {response.reason}")
        logging.debug(f"Error response details: {response.text}")
        return None

# Função principal
def main():
    # Carregar o arquivo JSON de salas
    with open("rooms.json", "r", encoding="utf-8") as file:
        rooms = json.load(file)

    # Carregar os usuários
    users = load_users("users.csv")

    # Criar as salas conforme especificado no JSON
    for room_name, room_users in rooms.items():
        first_user = room_users[0]
        invitees = [f"@{user}:dv.techsmart.space" for user in room_users[1:]]

        # Encontrar as credenciais do primeiro usuário
        user_credentials = next((user for user in users if user['username'] == first_user), None)
        
        if user_credentials:
            access_token = authenticate_user(MATRIX_SERVER, user_credentials['username'], user_credentials['password'])
            if access_token:
                create_room(MATRIX_SERVER, access_token, room_name, invitees)

# Executar o script
if __name__ == "__main__":
    main()
