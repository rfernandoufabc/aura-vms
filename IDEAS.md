# 💡 Ideias de Melhorias para o Aura VMS (Vizy)

> Este arquivo reúne ideias concretas para evoluir o sistema de gerenciamento de câmeras Vizy.
> Cada ideia está categorizada por área e estimativa de esforço.

---

## 🔐 Segurança e Autenticação

- **Autenticação de dois fatores (2FA):** Adicionar TOTP (Google Authenticator) ou SMS como segundo fator de login.
- **Registro de auditoria (audit log):** Registrar quem acessou qual câmera, quando e por quanto tempo, com interface de consulta para admins.
- **Sessões ativas:** Permitir que o usuário veja todos os dispositivos/sessões logados e possa encerrá-los remotamente.
- **Bloqueio por tentativas:** Bloquear IP ou conta após N tentativas de login falhas, com desbloqueio automático por tempo.
- **Tokens de API:** Gerar tokens pessoais de API para integração com scripts externos, sem expor a senha.
- **Permissões por faixa de horário:** Permitir que uma câmera só seja visualizável por um usuário dentro de um horário definido (ex: 08h–18h).

---

## 📷 Câmeras e Streaming

- **Preview em miniatura no sidebar:** Exibir um frame estático (snapshot) da câmera ao passar o mouse sobre ela na lista lateral da tela de visualização.
- **Snapshot programado:** Capturar frames das câmeras em intervalos regulares e armazená-los, criando um histórico visual.
- **Gravação de clipes:** Botão "Gravar" na tile da câmera que salva um clipe de N segundos do stream WebRTC.
- **Detecção de câmera offline:** Monitorar se a câmera está respondendo ao ping/RTSP e exibir alerta quando ficar offline.
- **Suporte a múltiplos streams (main/sub):** Alternar entre stream principal e sub-stream de menor resolução para economizar banda.
- **Status do go2rtc:** Painel mostrando quais streams estão ativos no go2rtc, com uptime e número de viewers.
- **Câmeras ONVIF:** Descoberta automática de câmeras ONVIF na rede local via broadcast.
- **Visualização em tela cheia nativa:** Botão de fullscreen direto na tile da câmera sem precisar abrir nova aba.
- **PTZ por software:** Interface de direcionamento para câmeras que suportam PTZ via ONVIF (movimento, zoom).

---

## 👥 Grupos e Permissões

- **Grupos aninhados:** Suporte a subgrupos para organização hierárquica (ex: Prédio A > Andar 2 > Câmeras).
- **Link de compartilhamento temporário:** Gerar um link de visualização de uma câmera ou grupo com expiração configurável, sem exigir cadastro.
- **Convite de usuário por e-mail:** Enviar convite por e-mail para adicionar um novo usuário ao sistema diretamente de um grupo.
- **Herdança de permissão:** Se um usuário pertence a um grupo, herdar automaticamente as permissões de câmeras do grupo pai.
- **Relatório de quem viu o quê:** Relatório exportável (CSV/PDF) com logs de visualização por câmera, grupo ou usuário.

---

## 🖥️ Interface e Experiência do Usuário

- **Tema claro:** Adicionar alternância entre tema escuro (atual) e tema claro.
- **Favoritos:** Marcar câmeras como favoritas para acesso rápido no topo da lista.
- **Arrastar para reordenar tiles:** Permitir reordenar os tiles de câmeras por drag-and-drop na tela de visualização.
- **Modo Quiosque:** Modo de exibição sem barra de navegação, ideal para monitores dedicados.
- **Notificações push no navegador:** Alertas do browser quando uma câmera fica offline ou é adicionada ao sistema.
- **Pesquisa de câmeras:** Campo de busca rápida na lista de câmeras por nome, IP ou modelo.
- **Indicador de latência:** Exibir latência do stream WebRTC em tempo real na tile da câmera.
- **Suporte a PWA (Progressive Web App):** Permitir instalar o Vizy como app no celular/desktop com ícone e modo offline básico.

---

## 📊 Dashboard e Relatórios

- **Widgets no dashboard:** Adicionar widgets configuráveis no dashboard: câmeras ativas, total de câmeras, usuários online, câmeras offline.
- **Histórico de eventos:** Log de eventos do sistema (câmera adicionada, usuário criado, visualização iniciada) com filtros de data/tipo.
- **Relatório de uso de banda:** Gráfico de consumo de dados por câmera ao longo do tempo.
- **Mapa de câmeras:** Visualizar câmeras em um mapa (Google Maps / OpenStreetMap) por localização geográfica cadastrada.
- **Exportar lista de câmeras:** Botão para exportar lista de câmeras em CSV ou JSON.

---

## 📧 Notificações

- **Alertas por e-mail:** Enviar e-mail quando uma câmera fica offline, quando um usuário faz login de novo dispositivo, ou quando o disco está quase cheio.
- **Webhook:** Configurar webhooks para enviar eventos do sistema para serviços externos (Slack, Discord, Zapier).
- **Notificação de câmera nova:** Notificar o admin master quando um usuário cadastra uma nova câmera.

---

## ⚙️ Infraestrutura e DevOps

- **Docker Compose pronto:** Publicar `docker-compose.yml` completo com Flask + go2rtc + Nginx configurados.
- **Variáveis de ambiente:** Mover todas as configurações sensíveis (SECRET_KEY, credenciais de e-mail, URL do go2rtc) para `.env`.
- **Migrações de banco com Flask-Migrate:** Substituir o sistema manual de migração por Alembic/Flask-Migrate.
- **Healthcheck endpoint:** Endpoint `/health` que retorna status do app e do go2rtc para monitoramento.
- **Suporte a PostgreSQL:** Abstrair a camada de dados para funcionar com PostgreSQL em produção além do SQLite para desenvolvimento.
- **Cache de sessões com Redis:** Usar Redis para armazenar sessões de usuário e o estado de viewers, garantindo consistência em múltiplos workers.
- **HTTPS automático com Let's Encrypt:** Script de provisionamento automático de certificado SSL para o domínio configurado.

---

## 📱 Mobile

- **App mobile (Flutter/React Native):** App nativo para iOS e Android com visualização de câmeras via WebRTC.
- **Biometria no app mobile:** Autenticação por digital ou Face ID no app mobile.
- **Widget de câmera favorita:** Widget na tela inicial do celular mostrando snapshot da câmera favorita.

---

## 🤖 Automação e IA (Ideias Avançadas)

- **Detecção de movimento local:** Processar o stream no servidor para detectar movimento e gerar alertas, usando OpenCV ou similar.
- **Reconhecimento de objetos:** Identificar pessoas, carros, animais no vídeo com modelo leve (YOLO) rodando localmente.
- **Análise de densidade:** Contar número de pessoas visíveis na câmera em tempo real para controle de lotação.
- **Detecção de câmera tampada/bloqueada:** Alertar quando a imagem da câmera ficar completamente preta ou coberta.
- **Linha virtual de cruzamento:** Definir uma linha na câmera e alertar quando alguém a cruzar.

---

> 💬 **Como usar este arquivo:** Revise cada ideia e marque as que fazem sentido para o momento atual do projeto.
> Priorize as que entregam mais valor com menor risco/esforço.
