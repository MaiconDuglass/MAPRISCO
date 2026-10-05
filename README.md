# Sistema MapRisco - Monitoramento de Áreas de Risco

## 📋 Descrição do Projeto

O **Sistema MapRisco** é uma aplicação web desenvolvida em Django para monitoramento de áreas de risco, com foco em detecção automática de enchentes e geração de alertas. O sistema integra interface web responsiva, API REST com autenticação JWT, e funcionalidades de georreferenciamento.

### 🎯 Objetivos
- Monitorar níveis de água em áreas de risco
- Gerar alertas automáticos quando níveis críticos são atingidos
- Fornecer interface visual com mapas interativos
- Oferecer dashboard com estatísticas em tempo real
- Garantir segurança através de autenticação robusta

## 🏗️ Arquitetura do Sistema

### Tecnologias Utilizadas
- **Backend**: Django 5.2 LTS (Python)
- **Banco de Dados**: PostgreSQL
- **API**: Django REST Framework
- **Autenticação**: JWT (JSON Web Tokens)
- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript
- **Mapas**: Leaflet.js
- **Gráficos**: Chart.js

### Estrutura de Pastas
```
MAPRISCO/
├── manage.py                 # Comando principal do Django
├── requirements.txt          # Dependências Python
├── README.md                 # Documentação completa
├── maprisco/                 # Configurações principais
│   ├── settings.py          # Configurações do Django
│   ├── urls.py              # URLs principais
│   ├── wsgi.py              # Configuração WSGI
│   └── asgi.py              # Configuração ASGI
├── apps/                     # Aplicações Django
│   ├── core/                 # Interface web e autenticação
│   │   ├── views.py         # Telas (mapa, dashboard, alertas, login...)
│   │   ├── forms.py         # Formulário de cadastro de usuário
│   │   ├── urls.py          # Rotas das telas
│   │   └── tests.py         # Testes das telas e do login
│   └── monitoramento/        # Regras de negócio e API
│       ├── models.py        # Áreas, medições e alertas (lógica automática no save)
│       ├── views.py         # ViewSets da API REST
│       ├── serializers.py   # Serializers da API (com geocodificação)
│       ├── permissions.py   # Permissões por perfil (cidadão x administrador)
│       ├── pagination.py    # Paginação da API (?page_size=)
│       ├── geocoding.py     # Busca de coordenadas pelo endereço (Nominatim)
│       ├── admin.py         # Painel administrativo
│       ├── management/      # Comandos (populate_parauapebas, geocodificar_areas)
│       └── migrations/      # Migrações do banco
├── static/                   # CSS, JS, Leaflet e logo
│   └── js/comum.js          # Funções JavaScript compartilhadas pelas telas
└── templates/                # Templates HTML
    ├── base.html            # Layout comum (barra lateral, barra superior)
    ├── index.html           # Mapa
    ├── dashboard.html       # Dashboard e cadastro de área
    ├── alertas.html         # Central de alertas
    ├── monitoramento.html   # Medições de nível de água
    ├── login.html           # Login
    └── register.html        # Cadastro de usuário
```

## 🚀 Guia de Instalação e Execução

### Pré-requisitos
- Python 3.8 ou superior
- PostgreSQL 12+
- Git

### Passo 1: Clonagem do Repositório
```bash
git clone <url-do-repositorio>
cd MAPRISCO
```

### Passo 2: Ambiente Virtual
```bash
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
# source venv/bin/activate
```

### Passo 3: Instalação de Dependências
```bash
pip install -r requirements.txt
```

### Passo 4: Configuração do Banco de Dados
```sql
-- Criar banco no PostgreSQL
CREATE DATABASE maprisco_db;
CREATE USER maprisco_user WITH PASSWORD 'sua_senha_segura';
GRANT ALL PRIVILEGES ON DATABASE maprisco_db TO maprisco_user;
```

### Passo 5: Configurações do Django
Edite `maprisco/settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'maprisco_db',
        'USER': 'maprisco_user',        # ALTERE AQUI
        'PASSWORD': 'sua_senha_segura', # ALTERE AQUI
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Configuração de Email (Recuperação de Senha)
A configuração de email é carregada a partir de variáveis de ambiente ou de um arquivo `.env` no diretório do projeto.

Crie um arquivo `.env` a partir de `.env.example` e atualize com suas credenciais:
```bash
copy .env.example .env
```

Edite `.env` com seus dados de SMTP:
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=seu-email@gmail.com
EMAIL_HOST_PASSWORD=sua-senha-de-app-ou-smtp
DEFAULT_FROM_EMAIL=no-reply@maprisco.local
```

> Para usar Gmail, pode ser necessário criar uma senha de app ou habilitar o recurso de app password.

### Passo 6: Migrações e Superusuário
```bash
# Aplicar as migrações (já estão no repositório)
python manage.py migrate

# Criar superusuário
python manage.py createsuperuser
```

### Passo 7: Executar Servidor
```bash
python manage.py runserver
```

### Passo 8: Acessar Sistema
- **Interface Web**: http://127.0.0.1:8000/
- **Admin Django**: http://127.0.0.1:8000/admin/
- **API REST**: http://127.0.0.1:8000/api/

## 🔐 Sistema de Autenticação

### Interface Web
- **Login**: http://127.0.0.1:8000/login/
- **Registro**: http://127.0.0.1:8000/register/
- **Logout**: http://127.0.0.1:8000/logout/

### API com JWT
```bash
# 1. Obter tokens
curl -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# Resposta:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}

# 2. Usar token na API
curl -H "Authorization: Bearer <access_token>" \
  http://127.0.0.1:8000/api/areas/
```

## 📊 Funcionalidades do Sistema

### 🗺️ Mapa Interativo
- **Visualização geográfica** de áreas de risco
- **Marcadores coloridos** por nível de risco:
  - 🟢 Verde: Risco baixo
  - 🟡 Amarelo: Risco médio
  - 🔴 Vermelho: Risco alto
- **Popups informativos** com detalhes das áreas
- **Centralizado** em São Paulo por padrão

### 📈 Dashboard Estatístico
- **Cards de métricas**:
  - Total de áreas cadastradas
  - Total de alertas gerados
  - Total de registros de monitoramento
- **Gráfico de distribuição** de níveis de risco
- **Lista de registros recentes**
- **Alertas mais recentes** com categorização visual

### 🔄 API REST Completa
| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/areas/` | GET/POST | Listar/Criar áreas |
| `/api/areas/<id>/` | GET/PUT/DELETE | Detalhar/Atualizar/Deletar área (alterar e deletar: só administrador) |
| `/api/monitoramento/` | GET/POST | Registros de monitoramento |
| `/api/alertas/` | GET/POST | Sistema de alertas |

### ⚡ Lógica Automática
- **Detecção crítica**: Quando nível de água > 80
- **Atualização automática** do status para "crítico"
- **Geração de alertas** críticos, com aviso por e-mail aos administradores
- **Processamento em tempo real** no `save()` do modelo `RegistroMonitoramento`

## 🧪 Testes do Sistema

### Teste da API com Postman
1. **Autenticação**:
   - POST `/api/token/` com credenciais
   - Copiar access_token

2. **Criar área de teste**:
   ```json
   POST /api/areas/
   {
     "nome": "Rio Tietê",
     "latitude": -23.550520,
     "longitude": -46.633308,
     "nivel_risco": "alto",
     "descricao": "Área crítica de monitoramento"
   }
   ```

3. **Criar registro crítico**:
   ```json
   POST /api/monitoramento/
   {
     "area": 1,
     "nivel_agua": 85.5,
     "status": "normal"
   }
   ```
   *Resultado*: Status alterado para "crítico" + alerta criado

### Teste da Interface Web
1. **Registro**: Criar nova conta
2. **Login**: Acessar sistema
3. **Mapa**: Visualizar áreas plotadas
4. **Dashboard**: Ver estatísticas atualizadas

## 📚 Documentação Técnica

### Modelos de Dados

#### AreaRisco
- `nome`: Nome da área
- `latitude/longitude`: Coordenadas geográficas
- `nivel_risco`: Classificação (baixo/médio/alto)
- `descricao`: Descrição opcional
- `data_criacao`: Timestamp

#### RegistroMonitoramento
- `area`: Referência à área
- `nivel_agua`: Medição em metros
- `status`: Estado atual
- `data_hora`: Timestamp

#### Alerta
- `area`: Área relacionada
- `mensagem`: Conteúdo do alerta
- `nivel`: Severidade
- `data_hora`: Timestamp

### Configurações Importantes

#### settings.py
- `DEBUG = True` (desenvolvimento)
- `ALLOWED_HOSTS = []` (localhost only)
- Database PostgreSQL configurado
- JWT authentication ativo
- Templates e static files configurados

#### Segurança Implementada
- ✅ Autenticação JWT obrigatória na API
- ✅ CSRF protection nas forms web
- ✅ Senhas hasheadas
- ✅ Headers de segurança do Django
- ✅ Validação de dados nos models

## 🔧 Dependências do Projeto

As versões exatas estão no `requirements.txt`. Principais:

```
Django==5.2.17
djangorestframework==3.16.1
djangorestframework-simplejwt==5.5.1
psycopg2-binary==2.9.7
```

## 📖 Considerações para TCC

### Pontos Fortes do Sistema
- ✅ **Arquitetura modular** com apps Django
- ✅ **API REST profissional** com documentação
- ✅ **Autenticação robusta** (JWT + sessão)
- ✅ **Interface responsiva** e moderna
- ✅ **Lógica de negócio automatizada**
- ✅ **Banco relacional** com integridade
- ✅ **Georreferenciamento** integrado

### Melhorias Futuras
- 🔄 **Notificações push** (email/SMS)
- 🔄 **Integração IoT** com sensores reais
- 🔄 **Relatórios PDF** automáticos
- 🔄 **API de clima** para previsões
- 🔄 **Testes automatizados** (unittest/pytest)
- 🔄 **Deploy em produção** (Docker/Heroku)

### Tecnologias Complementares
- **Redis**: Cache de dados
- **Celery**: Tarefas assíncronas
- **WebSockets**: Tempo real
- **Docker**: Containerização
- **Nginx**: Servidor web

## 👥 Informações do Projeto

- **Disciplina**: Trabalho de Conclusão de Curso
- **Curso**: [Nome do Curso]
- **Instituição**: [Nome da Instituição]
- **Desenvolvedor**: [Seu Nome]
- **Orientador**: [Nome do Orientador]
- **Data**: Abril 2026
- **Versão**: 1.0.0

## 📄 Conclusão

O Sistema MapRisco representa uma solução completa para monitoramento de áreas de risco, combinando tecnologias modernas web com práticas robustas de desenvolvimento. A implementação demonstra conhecimento avançado em Django, APIs REST, autenticação JWT, georreferenciamento e desenvolvimento frontend responsivo.

O sistema está **100% funcional** e pronto para demonstração em banca de TCC.

---

**Status do Projeto**: ✅ Concluído e Testado
**Data de Finalização**: Abril 2026

## Configuração

1. Instale Python 3.8+ se não tiver.
2. Crie um ambiente virtual: `python -m venv venv`
3. Ative o venv: `venv\Scripts\activate` (Windows)
4. Instale dependências: `pip install -r requirements.txt`
5. Configure o banco PostgreSQL: crie um banco chamado 'maprisco_db', usuário e senha.
6. Atualize settings.py com suas credenciais do banco.
7. Execute as migrações: `python manage.py migrate`
8. Rode o servidor: `python manage.py runserver`

Acesse http://127.0.0.1:8000/ para ver o frontend com mapa.

Acesse http://127.0.0.1:8000/dashboard/ para ver o dashboard com estatísticas.

## Autenticação

O sistema inclui autenticação completa:

### Páginas Web
- **Login**: `/login/` - Formulário de login
- **Registro**: `/register/` - Cadastro de novos usuários
- **Logout**: `/logout/` - Sair do sistema

### API JWT
- **Obter token**: `POST /api/token/` com `username` e `password`
- **Refresh token**: `POST /api/token/refresh/` com `refresh` token

### Proteção da API
Todas as rotas da API (`/api/*`) requerem autenticação JWT no header:
```
Authorization: Bearer <access_token>
```

### Como testar:

#### 1. Criar usuário via Django Admin ou API
Execute `python manage.py createsuperuser` para criar admin.

#### 2. Obter tokens
```bash
curl -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

#### 3. Usar token na API
```bash
curl -H "Authorization: Bearer <access_token>" \
  http://127.0.0.1:8000/api/areas/
```

#### 4. Com Postman
- POST para `/api/token/` para obter tokens
- Adicionar header `Authorization: Bearer <access_token>` nas outras requests

**Nota**: O frontend atual precisa ser atualizado para incluir autenticação JWT nas requests da API.

## Frontend

O frontend usa:
- **HTML/CSS**: Estrutura e estilos básicos
- **Bootstrap**: Framework CSS para responsividade
- **JavaScript**: Lógica para carregar dados
- **Leaflet.js**: Biblioteca para mapas interativos

### Funcionalidades:
- Mapa centrado em São Paulo
- Pontos coloridos por nível de risco (verde=baixo, amarelo=médio, vermelho=alto)
- Popups com informações das áreas
- Dados carregados automaticamente da API `/api/areas/`

### Como conectar com a API:
O JavaScript usa `fetch('/api/areas/')` para obter os dados JSON e plotar no mapa.

## Dashboard

Página em `/dashboard/` com:
- **Cards de estatísticas**: Total de áreas, alertas e registros
- **Gráfico**: Distribuição de níveis de risco (Chart.js)
- **Últimos registros**: Lista dos 5 registros mais recentes
- **Alertas recentes**: Cards dos 6 alertas mais recentes

Layout moderno com Bootstrap e gradientes.

### Como conectar com a API:
O JavaScript busca dados de `/api/areas/`, `/api/alertas/` e `/api/monitoramento/` para popular o dashboard.

## API REST

A API está disponível em `/api/` com os seguintes endpoints:

- `/api/areas/` - CRUD para Áreas de Risco
- `/api/monitoramento/` - CRUD para Registros de Monitoramento
- `/api/alertas/` - CRUD para Alertas
- `/api/examples/` - CRUD para Exemplos (do app core)

### Testando a API

#### Com Navegador
Acesse http://127.0.0.1:8000/api/ para ver a interface do DRF.

#### Com Postman
1. Abra o Postman.
2. Para listar: GET http://127.0.0.1:8000/api/areas/
3. Para criar: POST http://127.0.0.1:8000/api/areas/ com JSON body, ex.:
   ```json
   {
     "nome": "Área 1",
     "latitude": -23.550520,
     "longitude": -46.633308,
     "nivel_risco": "medio",
     "descricao": "Descrição da área"
   }
   ```
4. Para atualizar: PUT http://127.0.0.1:8000/api/areas/1/
5. Para deletar: DELETE http://127.0.0.1:8000/api/areas/1/

Use Content-Type: application/json nos headers.

## Lógica Automática

Quando um Registro de Monitoramento é criado ou atualizado:

- O status é calculado automaticamente: a partir de 80 cm = "crítico", a partir de 50 cm = "alerta", abaixo disso = "normal".
- Ao entrar no estado crítico, um alerta com nível "crítico" é criado automaticamente (uma única vez por escalada).
- Os administradores (`is_staff`) com e-mail cadastrado recebem um aviso por e-mail.

Isso é implementado no método `save()` do modelo `RegistroMonitoramento` (`apps/monitoramento/models.py`), dentro de uma transação.

## Estrutura

- `maprisco/`: Configurações do projeto
- `apps/core/`: App principal com modelos e views básicas

## Melhorias Implementadas

### Páginas Web
- `/alertas/`: Central de alertas com busca, filtros por nível/status e ação "marcar como resolvido".
- `/monitoramento/`: Cadastro de medições de nível de água (classificação automática) e histórico completo, com paginação e filtro por área.
- `/admin/`: Painel de administração do Django.
- Template base reutilizável (`templates/base.html`) com barra lateral, barra superior (alertas abertos e menu do usuário) e menu ☰ no celular.

### API
- Paginação (`?page=` e `?page_size=`, até 1000), busca (`?search=`) e ordenação (`?ordering=`) nos três endpoints.
- Filtro de medições por área: `GET /api/monitoramento/?area=<id>`.
- Endpoint `POST /api/alertas/<id>/resolver/` para resolver alertas.
- Throttling (limite de requisições) e CORS configurados.
- JWT com tempo de expiração limitado (30 min de acesso, 7 dias de refresh); refresh tokens antigos são invalidados após a rotação (`token_blacklist`).
- Permissões por perfil (`apps/monitoramento/permissions.py`):

| Ação | Visitante | Usuário (cidadão) | Administrador (`is_staff`) |
|------|-----------|-------------------|----------------------------|
| Ver mapa, áreas, alertas e registros (API) | ✅ | ✅ | ✅ |
| Acessar Dashboard, Alertas e Monitoramento | ❌ (vai para o login) | ✅ | ✅ |
| Cadastrar área / registrar medição | ❌ | ✅ | ✅ |
| Alterar ou apagar área / medição | ❌ | ❌ | ✅ |
| Resolver alertas | ❌ | ❌ | ✅ |

Para criar um administrador: `python manage.py createsuperuser`.

### Mapa
- Leaflet 1.9.4 servido localmente (`static/leaflet/`), sem depender de CDN.
- Camadas: Ruas (Esri World Street Map) e Satélite (Esri), com legenda de cores por nível de risco.
- No cadastro de área é possível clicar no mapa para marcar o local exato; sem marcação, a localização é obtida pelo endereço (geocodificação).
- Ao clicar numa área, o cartão mostra a última medição e um gráfico do nível de água ao longo do tempo, com as linhas de Alerta (50 cm) e Crítico (80 cm).
- Administradores podem editar e apagar áreas direto pelo mapa.

### Lógica de Negócio
- Classificação automática de status: nível ≥ 80 cm = crítico, ≥ 50 cm = alerta, senão normal.
- Geração de alerta (nível crítico) apenas na transição para o estado crítico, evitando duplicidade.
- Aviso por e-mail aos administradores quando um alerta crítico é gerado.
- Toda a lógica foi movida para `RegistroMonitoramento.save()` com `transaction.atomic`.
- `populate_parauapebas` não apaga dados existentes (usa `get_or_create`).

### Qualidade
- Testes automatizados em `apps/core/tests.py` e `apps/monitoramento/tests.py` (`python manage.py test`).
- Login e cadastro não diferenciam maiúsculas/minúsculas no e-mail.
- Logging configurado via variável `DJANGO_LOG_LEVEL`.
- Imagem enviada agora é validada (`ImageField` + limite de 5 MB).
- `ALLOWED_HOSTS`, CORS e demais configurações leitura do `.env`.