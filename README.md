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
│       ├── permissions.py   # Permissões da API (leitura pública, escrita só do administrador)
│       ├── pagination.py    # Paginação da API (?page_size=)
│       ├── geocoding.py     # Busca de coordenadas pelo endereço (Nominatim)
│       ├── admin.py         # Painel administrativo
│       ├── management/      # Comandos (cadastrar_areas_reais, dados_demo, relatos_demo, criar_usuario_demo, populate_parauapebas, geocodificar_areas)
│       └── migrations/      # Migrações do banco
├── static/                   # CSS, JS, Leaflet e logo
│   ├── js/comum.js          # Funções JavaScript compartilhadas pelas telas
│   └── js/mini_mapa.js      # Mini mapas (marcar um ponto / mostrar um ponto)
└── templates/                # Templates HTML
    ├── base.html            # Layout comum (barra lateral, barra superior)
    ├── index.html           # Mapa
    ├── dashboard.html       # Dashboard e cadastro de área
    ├── alertas.html         # Central de alertas
    ├── monitoramento.html   # Medições de nível de água
    ├── relatar.html         # Relato de alagamento do morador + "Meus relatos"
    ├── relatos.html         # Análise dos relatos (administrador)
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

### Passo 6.1: Áreas reais e dados de demonstração
```bash
# Cadastra as 4 áreas reais de risco de Parauapebas (ver "Áreas monitoradas")
python manage.py cadastrar_areas_reais

# Gera medições e alertas dos últimos 7 dias, para o dashboard e os gráficos não ficarem vazios
python manage.py dados_demo

# Cria o usuário comum de demonstração (a senha é digitada no terminal)
python manage.py criar_usuario_demo

# Cria 3 relatos de alagamento simulados (pendente, aprovado e rejeitado)
python manage.py relatos_demo
```
Detalhes na seção "Comandos de gerenciamento".

### Passo 7: Executar Servidor
```bash
python manage.py runserver
```

### Passo 8: Acessar Sistema
- **Interface Web**: http://127.0.0.1:8000/
- **Admin Django**: http://127.0.0.1:8000/admin/
- **API REST**: http://127.0.0.1:8000/api/

## 📍 Áreas monitoradas

O sistema monitora 4 áreas reais de risco de alagamento em Parauapebas-PA. São bairros citados pela
imprensa local como atingidos pelas cheias do rio Parauapebas e de igarapés. As coordenadas são o centro
aproximado de cada bairro no OpenStreetMap (Nominatim).

| Área | Bairro | Nível de risco | Motivo |
|------|--------|----------------|--------|
| Margem do Rio Parauapebas - Liberdade | Liberdade | Alto | Às margens do rio; um dos mais atingidos em dez/2021 e foco de vistorias da Defesa Civil em mar/2025 |
| Margem do Rio Parauapebas - Primavera | Primavera | Alto | Bairro ribeirinho com casas atingidas nas cheias de 2021 e 2025 |
| Margem do Rio Parauapebas - União | União | Alto | Próximo ao rio; entre os mais afetados em 2021 e 2025 |
| Igarapé Ilha do Coco - Novo Brasil | Novo Brasil | Médio | Transbordamento do igarapé Ilha do Coco em mar/2025 |

**Fontes:**
- DOL, 30/12/2021 — [Chuvas colocam Parauapebas sob risco de inundação](https://dol.com.br/carajas/cidades/parauapebas/689988/chuvas-colocam-parauapebas-sob-risco-de-inundacao)
- Diário do Pará, 06/03/2025 — [Defesa Civil emite alerta laranja para inundações no rio em Parauapebas](https://diariodopara.com.br/para/defesa-civil-emite-alerta-laranja-para-inundacoes-no-rio-em-parauapebas)
- SGB/CPRM — [Setorização de risco de Parauapebas](https://rigeo.sgb.gov.br/handle/doc/18347)

> As medições de nível de água geradas pelo comando `dados_demo` são **simuladas**, para demonstração.
> O sistema não está ligado a sensores reais.

## 🛠️ Comandos de gerenciamento

| Comando | O que faz |
|---------|-----------|
| `python manage.py cadastrar_areas_reais` | Cadastra (ou atualiza) as 4 áreas reais. Pode ser rodado várias vezes sem duplicar. |
| `python manage.py cadastrar_areas_reais --limpar-exemplos` | Além disso, apaga as 6 áreas fictícias antigas (Bacia do Rio Itacaiúnas, Área Urbana Centro, Vale do Rio Parauapebas, Região de Marabá, Reserva Ambiental Sul e Setor Industrial), **com suas medições e alertas**. |
| `python manage.py dados_demo` | Gera medições simuladas dos últimos 7 dias para as áreas reais, com níveis normal (< 50 cm), alerta (50 a 79 cm) e crítico (≥ 80 cm), e os alertas correspondentes (o mais recente fica em aberto). Áreas que já têm medições são ignoradas, então não duplica dados. Não envia e-mails. |
| `python manage.py criar_usuario_demo` | Cria (ou atualiza) o **usuário comum** de demonstração: e-mail `usuario.demo@maprisco.local`, nome "Usuário Demo". A senha é pedida no terminal (duas vezes) e passa pelas regras de senha do Django; ela não fica no código. O usuário nunca é administrador: se já existir, a senha e o nome são atualizados e ele volta a ser usuário comum. |
| `python manage.py relatos_demo` | Cria 3 relatos de alagamento **simulados** (a descrição começa com "Relato simulado para demonstração"): um pendente, um aprovado vinculado à área real do bairro Liberdade e um rejeitado com motivo. Rodar de novo não duplica; o aprovado ganha a data de agora, para voltar a aparecer na camada de 7 dias do mapa. Se o usuário demo existir, ele é o autor. Não cria medição, alerta nem e-mail. Rode depois de `cadastrar_areas_reais` (e de `criar_usuario_demo`, se quiser o usuário demo como autor). |
| `python manage.py populate_parauapebas` | Atalho mantido por compatibilidade: chama `cadastrar_areas_reais`. |
| `python manage.py geocodificar_areas` | Preenche latitude/longitude das áreas sem coordenadas, pelo endereço (Nominatim). |

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
- **Marcadores coloridos pela situação atual** de cada área, ou seja, pelo status da **última medição**:
  - 🟢 Verde (Seguro): última medição normal (abaixo de 50 cm)
  - 🟡 Amarelo (Alerta): última medição em alerta (50 a 79 cm)
  - 🔴 Vermelho (Crítico): última medição crítica (80 cm ou mais)
  - Área **sem nenhuma medição**: a cor usa o **nível de risco cadastrado** (baixo = verde, médio = amarelo, alto = vermelho)
- Os contadores do topo ("Áreas Críticas", "Em Alerta", "Seguras") e o filtro por situação seguem a mesma regra
- O cartão da área mostra separadamente a **situação atual** (ex.: "Normal (35,00 cm)") e o **nível de risco cadastrado** (ex.: "Alto"). Uma área de risco alto pode estar com o nível de água normal no momento.
- **Atualização automática** a cada 30 segundos (e ao voltar para a aba do mapa), sem mudar o zoom, os filtros nem o cartão aberto: ao registrar uma medição crítica em outra aba, o marcador fica vermelho sozinho. Se a atualização falhar, os dados na tela são mantidos.
- A API de áreas (`/api/areas/`) traz os campos somente leitura `ultimo_status`, `ultimo_nivel_agua` e `ultima_medicao_em` (todos `null` se a área não tem medição), calculados numa única consulta
- **Popups informativos** com detalhes das áreas
- **Centralizado** em Parauapebas-PA por padrão (`MAP_CENTER_LAT`, `MAP_CENTER_LNG` e `MAP_DEFAULT_ZOOM` em `maprisco/settings.py`)

### 📈 Dashboard Estatístico
- **Cards de métricas**:
  - Total de áreas cadastradas
  - Total de alertas gerados
  - Total de registros de monitoramento
- **Gráfico de distribuição** de níveis de risco
- **Lista de registros recentes**
- **Alertas mais recentes** com categorização visual
- **Relatos de moradores**: total aprovado (e, para o administrador, quantos aguardam análise)

### 🙋 Relato de alagamento (participação cidadã)

O morador ajuda a Defesa Civil avisando onde alagou. O fluxo é:

1. **Morador relata** (usuário logado, menu "Relatar alagamento"): informa rua, bairro, até onde chegou a água (estimativa), descrição e foto opcionais, e clica no mini mapa para marcar o local. Sem clique, o sistema tenta achar o local pelo endereço. O relato fica **pendente** e os administradores com e-mail cadastrado recebem um aviso.
2. **Administrador analisa** (menu "Relatos", com contador de pendentes): vê foto, local num mini mapa, nível estimado, bairro, data e quem enviou. Pode **aprovar**, vinculando o relato a uma área de risco existente (as mais próximas aparecem primeiro) ou criando uma área nova a partir dele, ou **rejeitar**, informando o motivo.
3. **Aprovado aparece no mapa** para todos, na camada "Relatos de moradores (últimos 7 dias)" (ícone roxo de pessoa), que pode ser ligada e desligada. O popup mostra rua, bairro, nível estimado e data, **nunca o nome do morador**.

Regras:
- Aprovar **não cria medição nem alerta**: o nível do morador é uma estimativa. Depois de aprovar, a tela oferece o atalho "Registrar medição nesta área", que abre o Monitoramento com a área já escolhida.
- Cada usuário pode enviar até **5 relatos a cada 24 horas** (acima disso a API responde 429 com uma mensagem amigável).
- O local precisa estar **dentro da região de Parauapebas** (a mesma usada na busca de endereço).
- Só relatos **pendentes** podem ser aprovados ou rejeitados.
- O morador acompanha seus relatos em "Meus relatos" (Pendente, Aprovado ou Rejeitado com o motivo).
- **LGPD**: nome e e-mail do autor só aparecem para administradores. O público não vê nem o motivo das rejeições.

### 🔄 API REST Completa
| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/areas/` | GET/POST | Listar (público) / Criar áreas (só administrador) |
| `/api/areas/<id>/` | GET/PUT/PATCH/DELETE | Detalhar (público) / Atualizar ou apagar área (só administrador) |
| `/api/monitoramento/` | GET/POST | Listar (público) / Registrar medição (só administrador) |
| `/api/alertas/` | GET | Listar alertas (público); alterar e resolver: só administrador |
| `/api/relatos/` | GET/POST | Relatos de alagamento: listar (cada perfil vê o que pode) / enviar (usuário logado) |
| `/api/relatos/<id>/aprovar/` | POST | Aprovar relato pendente (só administrador) |
| `/api/relatos/<id>/rejeitar/` | POST | Rejeitar relato pendente com motivo (só administrador) |

### ⚡ Lógica Automática
- **Detecção crítica**: quando o nível de água atinge 80 cm ou mais
- **Atualização automática** do status para "crítico"
- **Geração de alertas** críticos, com aviso por e-mail aos administradores
- **Processamento em tempo real** no `save()` do modelo `RegistroMonitoramento`

## 🧪 Testes do Sistema

### Teste da API com Postman
1. **Autenticação**:
   - POST `/api/token/` com credenciais
   - Copiar access_token

2. **Consultar uma área real** (bairro Liberdade, às margens do rio Parauapebas):
   ```
   GET /api/areas/?search=Liberdade
   ```
   Anote o `id` retornado (ele varia conforme o banco).

3. **Criar uma área**:
   ```json
   POST /api/areas/
   {
     "nome": "Margem do Rio Parauapebas - Liberdade",
     "bairro": "Liberdade",
     "cidade": "Parauapebas",
     "latitude": -6.081236,
     "longitude": -49.910355,
     "nivel_risco": "alto",
     "descricao": "Bairro às margens do rio Parauapebas, atingido nas cheias de 2021 e 2025."
   }
   ```
   *Observação*: se a área já estiver cadastrada (rua + bairro + cidade), a API responde 400 por duplicidade.

4. **Criar registro crítico** (use o `id` da área Liberdade obtido no passo 2):
   ```json
   POST /api/monitoramento/
   {
     "area": <id_da_area_liberdade>,
     "nivel_agua": 85.5
   }
   ```
   *Resultado*: status calculado como "crítico" + alerta criado automaticamente

### Teste da Interface Web
1. **Registro**: Criar nova conta
2. **Login**: Acessar sistema
3. **Mapa**: Visualizar áreas plotadas
4. **Dashboard**: Ver estatísticas atualizadas
5. **Perfis**: comparar visitante (aba anônima), usuário demo (`criar_usuario_demo`) e administrador, conforme a tabela "Permissões por perfil"

## 📚 Documentação Técnica

### Modelos de Dados

#### AreaRisco
- `nome`: Rua / endereço da área
- `bairro` e `cidade`: Localização (cidade padrão: Parauapebas)
- `latitude/longitude`: Coordenadas geográficas
- `foto`: Foto opcional (até 5 MB)
- `nivel_risco`: Classificação (baixo/médio/alto)
- `descricao`: Descrição opcional
- `data_criacao`: Timestamp

#### RegistroMonitoramento
- `area`: Referência à área
- `nivel_agua`: Medição em centímetros
- `status`: normal, alerta ou crítico (calculado automaticamente)
- `data_hora`: Timestamp

#### Alerta
- `area`: Área relacionada
- `mensagem`: Conteúdo do alerta
- `nivel`: Severidade
- `resolvido`: Se o alerta já foi tratado
- `data_hora`: Timestamp

#### RelatoAlagamento
- `autor`: Morador que enviou (visível só para administradores)
- `nome`, `bairro`, `cidade`: Local do alagamento
- `latitude`, `longitude`: Clique no mapa ou busca pelo endereço (dentro de Parauapebas)
- `nivel_estimado`: Na calçada/rua (até 10 cm), até o tornozelo (10 a 30 cm), até o joelho (30 a 50 cm) ou acima do joelho (mais de 50 cm)
- `descricao`, `foto`: Opcionais (foto até 5 MB)
- `status`: Pendente, aprovado ou rejeitado
- `area`: Área de risco vinculada na aprovação
- `analisado_por`, `analisado_em`, `motivo_rejeicao`: Dados da análise
- `data_hora`: Data do relato

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
- 🔄 **Notificações por SMS/push** (o aviso por e-mail já existe)
- 🔄 **Integração IoT** com sensores reais
- 🔄 **Relatórios PDF** automáticos
- 🔄 **Previsão de chuva** (hoje o mapa mostra a chuva atual via Open-Meteo)
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
A leitura (GET) é pública. Para cadastrar, alterar, apagar ou resolver alertas é preciso estar autenticado
(sessão do navegador ou JWT no header), conforme a tabela de permissões em "Melhorias Implementadas":
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

**Nota**: as telas web usam a sessão do Django (login normal); o JWT é usado por clientes externos (Postman, curl, apps).

## Frontend

O frontend usa:
- **HTML/CSS**: Estrutura e estilos básicos
- **Bootstrap**: Framework CSS para responsividade
- **JavaScript**: Lógica para carregar dados
- **Leaflet.js**: Biblioteca para mapas interativos

### Funcionalidades:
- Mapa centrado em Parauapebas-PA
- Pontos coloridos pela situação da última medição (verde=normal, amarelo=alerta, vermelho=crítico); sem medição, pelo nível de risco cadastrado
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

### Testando a API

#### Com Navegador
Acesse http://127.0.0.1:8000/api/ para ver a interface do DRF.

#### Com Postman
1. Abra o Postman.
2. Para listar: GET http://127.0.0.1:8000/api/areas/
3. Para criar: POST http://127.0.0.1:8000/api/areas/ com JSON body, ex.:
   ```json
   {
     "nome": "Igarapé Ilha do Coco - Novo Brasil",
     "bairro": "Novo Brasil",
     "cidade": "Parauapebas",
     "latitude": -6.090191,
     "longitude": -49.867560,
     "nivel_risco": "medio",
     "descricao": "Alagamento pelo transbordamento do igarapé Ilha do Coco (mar/2025)."
   }
   ```
4. Para atualizar: PUT http://127.0.0.1:8000/api/areas/1/
5. Para deletar: DELETE http://127.0.0.1:8000/api/areas/1/

Use Content-Type: application/json nos headers. Para PUT/DELETE é preciso ser administrador.

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
- `/alertas/`: Central de alertas com busca, filtros por nível/status e ação "marcar como resolvido" (só administrador).
- `/monitoramento/`: (só administrador) Cadastro de medições de nível de água (classificação automática) e histórico completo, com paginação e filtro por área.
- `/admin/`: Painel de administração do Django.
- Template base reutilizável (`templates/base.html`) com barra lateral, barra superior (alertas abertos e menu do usuário) e menu ☰ no celular.

### API
- Paginação (`?page=` e `?page_size=`, até 1000), busca (`?search=`) e ordenação (`?ordering=`) nos três endpoints.
- Filtro de medições por área: `GET /api/monitoramento/?area=<id>`.
- Endpoint `POST /api/alertas/<id>/resolver/` para resolver alertas.
- Throttling (limite de requisições) e CORS configurados.
- JWT com tempo de expiração limitado (30 min de acesso, 7 dias de refresh); refresh tokens antigos são invalidados após a rotação (`token_blacklist`).
- Permissões por perfil: na API (`apps/monitoramento/permissions.py`, classe `LeituraPublicaEscritaSomenteAdmin`) e nas páginas (`apps/core/views.py`, decorador `admin_required`). Esconder o botão não basta: a API recusa com **403** quem não é administrador.

#### Permissões por perfil

| O quê | Visitante (sem login) | Usuário comum | Administrador (`is_staff`) |
|-------|-----------------------|---------------|----------------------------|
| Menu lateral | Mapa | Mapa, Dashboard, Alertas | Mapa, Dashboard, Cadastrar Área, Alertas, Monitoramento, Usuários |
| Sino de alertas na barra superior | ❌ (não aparece) | ✅ | ✅ |
| Mapa: áreas, situação atual, histórico e gráfico | ✅ | ✅ | ✅ |
| Mapa: "Registrar medição", Editar e Apagar | ❌ | ❌ | ✅ |
| Dashboard (consulta) | ❌ (vai para o login) | ✅ | ✅ |
| Cadastrar área (botão, formulário e `/dashboard/?nova=1`) | ❌ (vai para o login) | ❌ (volta ao mapa com aviso) | ✅ |
| Alertas (consulta) | ❌ (vai para o login) | ✅ | ✅ |
| Resolver alerta | ❌ | ❌ | ✅ |
| Página de Monitoramento (`/monitoramento/`) | ❌ (vai para o login) | ❌ (volta ao mapa com aviso) | ✅ |
| API: ler áreas, medições e alertas | ✅ | ✅ | ✅ |
| API: criar, alterar ou apagar área / medição | ❌ (401/403) | ❌ (403) | ✅ |
| API: alterar ou resolver alerta | ❌ (401/403) | ❌ (403) | ✅ |
| Menu "Relatar alagamento" e envio de relato | ❌ (convite para entrar no mapa) | ✅ (até 5 em 24 h) | ✅ |
| Ver relatos aprovados no mapa (sem autor) | ✅ | ✅ | ✅ |
| Ver os próprios relatos pendentes/rejeitados ("Meus relatos") | ❌ | ✅ | ✅ |
| Menu "Relatos" (análise, com contador de pendentes) | ❌ | ❌ (volta ao mapa com aviso) | ✅ |
| Ver todos os relatos, com nome e e-mail do autor | ❌ | ❌ | ✅ |
| Aprovar ou rejeitar relato | ❌ | ❌ (403) | ✅ |

O aviso para o usuário comum é "Esta função é exclusiva da administração.". Assim ninguém de fora cria áreas falsas nem medições falsas (que gerariam alertas críticos e e-mails para a Defesa Civil).

Para criar um administrador: `python manage.py createsuperuser`. Para o usuário comum de demonstração: `python manage.py criar_usuario_demo`.

### Mapa
- Leaflet 1.9.4 servido localmente (`static/leaflet/`), sem depender de CDN.
- Camadas: Ruas (Esri World Street Map) e Satélite (Esri), com legenda de cores pela situação atual (última medição).
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
- 67 testes automatizados em `apps/core/tests.py` e `apps/monitoramento/tests.py` (`python manage.py test`).
- Login e cadastro não diferenciam maiúsculas/minúsculas no e-mail.
- Logging configurado via variável `DJANGO_LOG_LEVEL`.
- Imagem enviada agora é validada (`ImageField` + limite de 5 MB).
- `ALLOWED_HOSTS`, CORS e demais configurações leitura do `.env`.