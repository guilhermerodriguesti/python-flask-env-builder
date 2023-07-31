import os
import requests
import base64
import json
from flask import Flask, request, render_template, redirect
from loguru import logger
from dotenv import load_dotenv, dotenv_values

app = Flask(__name__)

# Carregando as variáveis de ambiente do arquivo .env
load_dotenv()

# Obtendo as variáveis de ambiente do arquivo .env
username = os.getenv('BITBUCKET_USERNAME')
password = os.getenv('BITBUCKET_APP_PASSWORD')
token = os.getenv('BITBUCKET_ACCESS_TOKEN')
account = os.getenv('BITBUCKET_REPO_OWNER')

BITBUCKET_API_BASE_URL = "https://api.bitbucket.org/2.0"

def parse_env_file(file_path):
    env_data = {}
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_data[key] = value
    return env_data

def deploy_to_bitbucket(env_data, environment, repository):
    # Implement your logic here to deploy the data to Bitbucket
    # This may involve using the Bitbucket API or some other method
    # You can use the 'environment' and 'repository' variables here
    pass

def get_bitbucket_access_token(username, password):
    """Obtém o token de acesso do Bitbucket usando o nome de usuário e senha."""
    access_token = username + password
    access_token = access_token.encode("ascii")
    access_token = base64.b64encode(access_token)
    access_token = access_token.decode("ascii")
    return access_token

def get_deployment_environments(api_base_url, workspace_slug, repo_slug, access_token):
    """Obtém os ambientes de implantação disponíveis do Bitbucket."""
    headers = {'Authorization': f'Basic {access_token}'}
    url = f'{api_base_url}/2.0/repositories/{workspace_slug}/{repo_slug}/environments/'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['values']

def sync_variables(api_base_url, workspace_slug, repo_slug, environment_uuid, access_token, config):
    """Sincroniza as variáveis do arquivo com os ambientes de implantação disponíveis."""
    headers = {'Authorization': f'Basic {access_token}'}
    for key, value in config.items():
        url = f'{api_base_url}/2.0/repositories/{workspace_slug}/{repo_slug}/deployments_config/environments/{environment_uuid}/variables'
        payload = {
            'key': key,
            'value': value,
            'secured': False
        }
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

@app.route('/deploy/<filename>', methods=['POST'])
def deploy_file(filename):
    # Extrai o projeto e o ambiente do nome do arquivo
    parts = filename.split('_')
    if len(parts) != 2:
        return "Invalid file format"

    project, environment = parts

    # Carrega as variáveis de ambiente do arquivo
    file_path = os.path.join("uploads", filename)
    config = dotenv_values(file_path)

    try:
        # Obtendo as informações do formulário
        username = request.form.get('username')
        password = request.form.get('password')
        workspace_slug = request.form.get('workspace_slug')
        repo_slug = request.form.get('repo_slug')

        # Verificando se todas as informações foram fornecidas
        if not all([oauth_consumer_key, oauth_secret_key, username, password, workspace_slug, repo_slug]):
            return "Missing information in the form. Please provide all required fields."

        # Obtendo o access token do Bitbucket
        access_token = get_bitbucket_access_token(username, password)
        api_base_url = 'https://api.bitbucket.org'

        # Obtendo os ambientes de implantação disponíveis do Bitbucket
        deployment_environments = get_deployment_environments(api_base_url, workspace_slug, repo_slug, access_token)

        for deployment_environment in deployment_environments:
            environment_name = deployment_environment['name']
            if environment_name.lower() == environment.lower():
                sync_variables(api_base_url, workspace_slug, repo_slug, deployment_environment['uuid'], access_token, config)
                break

        return redirect('/file_list')

    except requests.exceptions.RequestException as e:
        logger.exception(str(e))
        return "Error occurred during synchronization. Please check the logs."

@app.route('/file_list', methods=['GET'])
def file_list():
    # Obtenha a lista de arquivos na pasta "uploads"
    files = os.listdir("uploads")
    return render_template('file_list.html', files=files)

@app.route('/', methods=['GET'])
def home():
    return render_template('home.html', projects=get_projects())

@app.route('/upload', methods=['GET', 'POST'])
def upload_env_file():
    if request.method == 'POST':
        if 'env_file' not in request.files:
            return "No file part"
        
        env_file = request.files['env_file']
        environment = request.form['environment']
        #project = request.form['project']
        #team = request.form['team']
        repository = request.form['repository']

        if env_file.filename == '':
            return "No selected file"
        
        if env_file and env_file.filename.endswith('env.example'):
            # Modify the file name to include the environment, project, team, and repository
            file_name = f"{repository}_{environment}.env"
            file_path = os.path.join("uploads", file_name)

            # Create the 'uploads' directory if it doesn't exist
            os.makedirs("uploads", exist_ok=True)

            env_file.save(file_path)
            env_data = parse_env_file(file_path)
            deploy_to_bitbucket(env_data, environment, repository)
            success_message = "File uploaded and deployed successfully!"

            # Read the content of the .env file
            with open(file_path, 'r') as env_file:
                file_content = env_file.read()

            return render_template('upload.html', success_message=success_message, file_content=file_content, projects=get_projects())
        else:
            error_message = "Invalid file type. Please upload an .env file."
            return render_template('upload.html', error_message=error_message, projects=get_projects())

    # If the request method is GET, simply return the upload.html page
    return render_template('upload.html', projects=get_projects())

@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    file_path = os.path.join("uploads", filename)
    try:
        # Remove o arquivo do sistema de arquivos
        os.remove(file_path)
        return redirect('/file_list')
    except Exception as e:
        logger.exception(str(e))
        return "Error occurred during file deletion. Please check the logs."

@app.route('/edit/<filename>', methods=['GET', 'POST'])
def edit_file(filename):
    file_path = os.path.join("uploads", filename)

    if request.method == 'POST':
        # Se o formulário for enviado com os dados de edição, salve-os no arquivo
        edited_content = request.form['edited_content']
        with open(file_path, 'w') as file:
            file.write(edited_content)
        
        # Redirecione o usuário de volta para a lista de arquivos após a edição
        return redirect('/file_list')

    # Se a rota for acessada com o método GET, leia o conteúdo do arquivo
    with open(file_path, 'r') as file:
        file_content = file.read()

    return render_template('edit_file.html', file_name=filename, file_content=file_content)

def get_projects():
    with open("projects.json", "r") as json_file:
        data = json.load(json_file)
        projects = data.get("projects", [])
    return projects
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
