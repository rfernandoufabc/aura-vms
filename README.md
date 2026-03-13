<div align="center">

# Vizy

<img src="https://github.com/user-attachments/assets/7acfc240-3fc8-49e3-8e2a-e0615171e513" alt="Vizy Logo" width="200">

### *Vigilância Inteligente para Comunidades Conectadas*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org)
[![go2rtc](https://img.shields.io/badge/go2rtc-streaming-00ADD8?style=for-the-badge&logo=go&logoColor=white)](https://github.com/AlexxIT/go2rtc)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

> **"Porque cada segundo importa quando alguém está perdido."**

</div>

---

## 🌟 A História por Trás do Vizy

Imagine a seguinte cena: é uma tarde de sábado, o sol ainda está alto, e a Maria — uma senhora de 72 anos moradora do Bairro das Acácias — não voltou do mercadinho que fica a duas quadras de casa. Sua família começa a ligar, os vizinhos se mobilizam, mas ninguém sabe por onde começar a procurar.

Ou então: o Totó, um golden retriever de 4 anos e melhor amigo do Pedro (8 anos), fugiu pelo portão aberto durante a tarde. Toda a família está desesperada.

**Em ambos os casos, a pergunta é a mesma: *alguém viu?***

É exatamente para responder a essa pergunta — de forma rápida, organizada e eficiente — que o **Vizy** foi criado.

---

## 🔍 O que é o Vizy?

O **Vizy** é uma **plataforma de gerenciamento de câmeras de segurança** desenvolvida em Python com Flask, que transforma câmeras IP comuns espalhadas por um bairro em uma **rede colaborativa de vigilância comunitária**.

A plataforma permite que moradores, condomínios, comércios locais e associações de bairro **cadastrem suas câmeras**, **compartilhem acesso seletivamente** e **visualizem feeds ao vivo diretamente no navegador** — sem precisar instalar nenhum software adicional.

> 💡 **A grande sacada:** em vez de cada câmera ficar isolada no seu próprio DVR, o Vizy conecta todas elas numa rede colaborativa, onde o acesso é controlado por permissões granulares e grupos. É o poder da comunidade, organizado digitalmente.

---

## 🎯 Casos de Uso Reais

### 🧓 Pessoa Perdida no Bairro

**Cenário:** Um idoso com Alzheimer saiu de casa e a família não sabe para onde foi.

**Com o Vizy:**
1. A família aciona o grupo `"Bairro das Acácias — Segurança"` no sistema
2. Os operadores autorizados acessam simultaneamente os feeds de múltiplas câmeras: padaria, farmácia, esquina da rua principal, praça central
3. Em poucos minutos, identificam a última câmera que registrou a passagem do idoso
4. As informações são compartilhadas com a família e com os moradores próximos
5. O idoso é encontrado e levado com segurança para casa

**Sem o Vizy:** cada câmera estaria num sistema diferente, exigiria senha individual, e a coordenação levaria horas — tempo que pode ser crítico.

---

### 🐾 Animal Perdido no Bairro

**Cenário:** Um cachorro ou gato fugiu de casa e o tutor não sabe por onde procurar.

**Com o Vizy:**
1. O tutor acessa o painel e visualiza as câmeras do bairro em tempo real
2. Identifica o trajeto do animal pelas imagens cronológicas
3. Notifica vizinhos próximos ao local onde o animal foi visto por último
4. O pet é encontrado e resgatado

**Diferencial:** como a plataforma é baseada em streaming ao vivo via WebRTC, não é necessário aguardar pela gravação — o tutor pode acompanhar os feeds em tempo real e orientar resgatadores pelo telefone simultaneamente.

---

### 🏘️ Outros Cenários de Aplicação

| Situação | Como o Vizy Ajuda |
|---|---|
| 🚗 Carro riscado na rua | Identifica o responsável pelas câmeras da via |
| 👶 Criança não voltou da escola | Monitora o trajeto escola-casa pelas câmeras da rota |
| 🏠 Furto em residência | Coordena a visualização das câmeras vizinhas para identificar suspeitos |
| 🌪️ Emergência climática | Permite monitorar pontos críticos do bairro (alagamentos, quedas de árvore) |
| 🎉 Eventos comunitários | Compartilha temporariamente o acesso com organizadores |

---

## 🏗️ Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────┐
│                     NAVEGADOR DO USUÁRIO                 │
│              (WebRTC — sem instalação!)                  │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS / WSS
┌──────────────────────▼──────────────────────────────────┐
│                     VIZY (Flask)                      │
│   ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  │
│   │  Autenticação│  │  Gerenciamento│  │  Permissões  │  │
│   │  + Sessões  │  │  de Câmeras  │  │  e Grupos    │  │
│   └─────────────┘  └──────────────┘  └──────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       │ API REST
┌──────────────────────▼──────────────────────────────────┐
│                      go2rtc                              │
│         (Relay RTSP → WebRTC / HLS / MSE)               │
└──────────────────────┬──────────────────────────────────┘
                       │ RTSP
┌──────────────────────▼──────────────────────────────────┐
│              CÂMERAS IP DO BAIRRO                        │
│   [Hikvision] [Dahua] [V380] [Intelbras] [Genéricas]    │
└─────────────────────────────────────────────────────────┘
```

### Como funciona o fluxo de streaming?

1. **Registro da câmera:** o usuário cadastra o IP, porta, credenciais e marca da câmera
2. **Geração automática da URL RTSP:** o sistema monta a URL de streaming de acordo com o modelo da câmera (cada fabricante tem seu próprio formato)
3. **Relay via go2rtc:** ao abrir o feed, o Vizy instrui o go2rtc a se conectar à câmera via RTSP e re-transmitir o sinal como WebRTC
4. **Visualização no navegador:** o usuário assiste ao vivo, diretamente no navegador, sem plugins, sem VPN, sem DVR dedicado

---

## ✨ Funcionalidades Principais

### 🔐 Autenticação e Gestão de Usuários
- Cadastro com verificação de e-mail por token seguro
- Login com sessão protegida
- Recuperação de senha por e-mail (link com expiração de 1 hora)
- Níveis de acesso: **Usuário comum**, **Administrador** e **Admin Master**

### 📷 Gerenciamento de Câmeras
- Cadastro de câmeras com suporte a múltiplas marcas (Hikvision, Dahua, V380, Yoosee, ONVIF e genéricas)
- Detecção automática do template RTSP por marca/modelo
- Pré-visualização da URL RTSP antes de salvar
- Exibição opcional do contador de visualizadores ativos

### 👥 Grupos e Permissões Granulares
- Criação de grupos (ex: `"Câmeras da Rua das Flores"`, `"Portaria do Condomínio Bela Vista"`)
- Adição de membros ao grupo
- Permissão por câmera: `visualizar` e/ou `controlar` (PTZ)
- Permissões individuais por usuário ou coletivas por grupo

### 🎥 Visualização ao Vivo
- Feed WebRTC nativo no navegador (sem instalação de plugins)
- Suporte a múltiplas câmeras simultaneamente
- Detecção automática do servidor go2rtc (local ou em nuvem)
- Suporte a domínios personalizados com HTTPS (`video.seudominio.com.br`)

### 🛡️ Painel Administrativo
- Listagem e edição de todos os usuários
- Transferência de câmeras entre usuários
- Gerenciamento completo de permissões
- Controle total pelo Admin Master (`admin`)

---

## 📊 Modelo de Dados

```
User ─────────── Camera ─────────── Permission
 │                  │                    │
 │              CameraApp            (user ↔ camera)
 │              CameraModel
 │
 ├── Group ──── GroupMember
 │       │
 │       └──── GroupPermission
 │                   │
 │               (group ↔ camera)
 │
 └── AuthToken (confirm / reset)
```

| Entidade | Descrição |
|---|---|
| `User` | Conta de acesso ao sistema |
| `Camera` | Câmera IP registrada com credenciais RTSP |
| `CameraApp` | Template de URL RTSP por fabricante |
| `CameraModel` | Modelos específicos de câmera |
| `Permission` | Permissão individual usuário ↔ câmera |
| `Group` | Grupo de usuários para acesso coletivo |
| `GroupMember` | Associação usuário ↔ grupo |
| `GroupPermission` | Permissão coletiva grupo ↔ câmera |
| `AuthToken` | Token de confirmação de e-mail ou reset de senha |

---

## 🚀 Instalação e Execução

### Pré-requisitos

- Python 3.10+
- [go2rtc](https://github.com/AlexxIT/go2rtc/releases) (para streaming WebRTC)
- Acesso à rede local onde as câmeras estão conectadas

### 1. Clone o repositório

```bash
git clone https://github.com/rfernandoufabc/vizy.git
cd vizy
```

### 2. Crie o ambiente virtual e instale as dependências

```bash
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# ou
.venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

### 3. Configure as variáveis de ambiente

```bash
# Opcional — o sistema usa valores padrão se não definidos
export SECRET_KEY="sua-chave-secreta-forte-aqui"
export GO2RTC_URL="http://localhost:1984"
export BASE_URL="http://localhost:5000"

# Para envio de e-mails (confirmação e reset de senha)
export MAIL_SERVER="smtp.gmail.com"
export MAIL_PORT="587"
export MAIL_USERNAME="seu-email@gmail.com"
export MAIL_PASSWORD="sua-senha-de-app"
```

### 4. Inicie o go2rtc

```bash
# Baixe o binário em https://github.com/AlexxIT/go2rtc/releases
./go2rtc
# Por padrão, sobe na porta 1984
```

### 5. Execute o Vizy

```bash
python app.py
```

Acesse: **http://localhost:5000**

Login inicial: `admin` / `admin123` *(troque a senha imediatamente!)*

---

## 🌐 Deploy em Produção

Para um bairro real, recomendamos:

```
Internet
    │
    ▼
[Servidor na Nuvem ou VPS]
    ├── Nginx (porta 443 / HTTPS)
    │       ├── / → Vizy (Gunicorn, porta 5000)
    │       └── video.seudominio.com → go2rtc (porta 1984)
    └── go2rtc (com acesso VPN/tunnel às câmeras locais)
```

O Vizy detecta automaticamente se está rodando em localhost/IP local ou num domínio e ajusta a URL do go2rtc de acordo — sem configuração manual adicional.

---

## 💼 Proposta de Valor para Comunidades

### O Problema Atual

- Câmeras de segurança ficam **isoladas** em sistemas proprietários
- Em emergências, é necessário **ligar para cada vizinho individualmente** para pedir acesso ao DVR
- Sistemas profissionais de monitoramento custam **centenas a milhares de reais por mês**
- Não existe uma forma simples de **coordenar a busca** por pessoas ou animais perdidos

### A Solução Vizy

| Aspecto | Solução Tradicional | Vizy |
|---|---|---|
| 💰 Custo | R$ 500–5000/mês (monitoramento profissional) | Software gratuito; infraestrutura a partir de R$ 50/mês (VPS) |
| 🛠️ Instalação | Técnico especializado | Qualquer pessoa com Python |
| 📱 Acesso | App proprietário, VPN, DVR físico | Qualquer navegador moderno |
| 🤝 Colaboração | Impossível entre vizinhos | Nativa, com controle de permissões |
| 🔐 Privacidade | Dados em servidores de terceiros | 100% na infraestrutura da comunidade |
| 🔍 Busca emergencial | Horas de coordenação | Minutos com acesso centralizado |

### Modelo de Negócio Sugerido

```
┌─────────────────────────────────────────┐
│  ASSOCIAÇÃO DE MORADORES / CONDOMÍNIO   │
│                                         │
│  Paga uma mensalidade simbólica para    │
│  hospedagem e manutenção do sistema     │
│  (ex: R$ 50–200/mês para um VPS)        │
└─────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────┐
│  MORADORES / COMÉRCIOS DO BAIRRO        │
│                                         │
│  Cadastram suas câmeras gratuitamente   │
│  e compartilham acesso com a            │
│  associação em casos de emergência      │
└─────────────────────────────────────────┘
```

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologia | Por quê? |
|---|---|---|
| **Backend** | Python + Flask | Simples, robusto, enorme ecossistema |
| **Banco de Dados** | SQLite / SQLAlchemy | Zero configuração para começar; migrável para PostgreSQL |
| **Autenticação** | Werkzeug + itsdangerous | Hashing seguro, tokens assinados |
| **Streaming** | go2rtc | Suporte nativo a RTSP→WebRTC, HLS, MSE; zero latência |
| **Frontend** | Jinja2 + CSS puro | Sem dependência de frameworks JS; leve e com mínimas dependências externas |
| **E-mail** | Flask-Mail | Confirmação de conta e reset de senha |

---

## 🗺️ Roadmap

- [ ] 📱 **App Mobile** — visualização responsiva otimizada para smartphones
- [ ] 🔔 **Alertas por Push** — notificação em tempo real ao detectar movimento
- [ ] 🤖 **Integração com IA** — detecção de pessoas e animais via visão computacional
- [ ] 🗺️ **Mapa do Bairro** — exibição georreferenciada das câmeras num mapa interativo
- [ ] 📼 **Gravação sob demanda** — iniciar gravação remota em caso de emergência
- [ ] 🔗 **API pública** — integração com aplicativos de bairro (Nextdoor, grupos de WhatsApp via bot)
- [ ] 🌍 **Multi-idioma** — suporte a inglês e espanhol

---

## 🤝 Contribuindo

Contribuições são muito bem-vindas! Este projeto nasceu de uma necessidade real de comunidades brasileiras e acredita no poder do software livre para resolver problemas sociais.

1. Fork o repositório
2. Crie uma branch para sua feature: `git checkout -b feature/minha-feature`
3. Commit suas mudanças: `git commit -m 'Adiciona minha feature'`
4. Push para a branch: `git push origin feature/minha-feature`
5. Abra um Pull Request

---

## 📄 Licença

Este projeto está licenciado sob a [MIT License](LICENSE) — use, modifique e distribua livremente, inclusive para fins comerciais.

---

<div align="center">

**Desenvolvido com 💜 para comunidades brasileiras**

*"Tecnologia que aproxima vizinhos e salva vidas."*

</div>