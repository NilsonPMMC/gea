import requests
from decouple import config

# Carrega chaves
APP_ID = config('COLAB_APP_ID', default='')
API_KEY = config('COLAB_API_KEY', default='')
USER_TOKEN = config('COLAB_USER_TOKEN', default='')

URL = "https://api.colabapp.com/v2/integration/posts"

print(f"Testando URL: {URL}")

# --- TENTATIVA 1: Headers Customizados (Padrão Parse/Colab antigo) ---
headers1 = {
    'X-App-Id': APP_ID,
    'X-Rest-API-Key': API_KEY,
    'Content-Type': 'application/json'
}
try:
    r1 = requests.get(URL, headers=headers1)
    print(f"Tentativa 1 (X-App-Id): {r1.status_code}")
except: print("Tentativa 1: Falhou conexão")

# --- TENTATIVA 2: Basic Auth (Usuário e Senha) ---
try:
    r2 = requests.get(URL, auth=(APP_ID, API_KEY))
    print(f"Tentativa 2 (Basic Auth): {r2.status_code}")
except: print("Tentativa 2: Falhou conexão")

# --- TENTATIVA 3: Bearer Token (Usando o User Token) ---
headers3 = {
    'Authorization': f'Bearer {USER_TOKEN}',
    'Content-Type': 'application/json'
}
try:
    r3 = requests.get(URL, headers=headers3)
    print(f"Tentativa 3 (Bearer Token): {r3.status_code}")
except: print("Tentativa 3: Falhou conexão")

# --- TENTATIVA 4: Headers Exatos da Documentação ---
print("\n--- Tentativa 4: Headers Específicos do Colab ---")
headers4 = {
    'x-colab-application-id': APP_ID,
    'x-colab-rest-api-key': API_KEY,
    'x-colab-admin-user-auth-ticket': USER_TOKEN, # Aqui entra o seu User Token
    'Content-Type': 'application/json'
}

# Debug: Imprimir os headers (escondendo parte das chaves por segurança)
print(f"Enviando Application ID: {APP_ID[:5]}...")
print(f"Enviando Auth Ticket: {USER_TOKEN[:5]}...")

try:
    r4 = requests.get(URL, headers=headers4)
    print(f"Status Code: {r4.status_code}")
    if r4.status_code == 200:
        print("SUCESSO! Conexão estabelecida.")
        print("Primeiros 100 caracteres da resposta:", r4.text[:100])
    else:
        print("Erro:", r4.text)
except Exception as e: 
    print(f"Falha na conexão: {e}")