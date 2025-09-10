import requests

# URL del endpoint
url = "http://localhost:8199/api/purchase/orders"

# Autenticación con API Key
headers = {
}

# Hacer la solicitud GET
response = requests.get(url, headers=headers)

# Mostrar la respuesta JSON
if response.status_code == 200:
    print(response.json())
else:
    print("Error:", response.status_code, response.text)
