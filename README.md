# n8n SSL Certificate Monitor

🇧🇷 **Português** | [🇺🇸 English](#-english-version)

Workflow do [n8n](https://n8n.io) que monitora diariamente a validade de certificados SSL/TLS e envia alertas via WhatsApp (UazAPI) quando um certificado está próximo de expirar ou já expirou.

![n8n](https://img.shields.io/badge/n8n-2.0%2B-EA4B71?logo=n8ndotio&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-stable-brightgreen)


<img width="1166" height="628" alt="Captura de Tela 2026-04-23 às 19 47 42" src="https://github.com/user-attachments/assets/6187b44d-21a6-4216-bf9d-fc1dc3f0f5fd" />


---

## Sumário

- [O que faz](#o-que-faz)
- [Diagrama do fluxo](#diagrama-do-fluxo)
- [Como funciona](#como-funciona)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Estrutura da planilha](#estrutura-da-planilha)
- [Exemplo de alerta](#exemplo-de-alerta)
- [Personalização](#personalização)
- [Troubleshooting](#troubleshooting)
- [Contribuição](#contribuição)
- [Licença](#licença)

---

## O que faz

Todo dia às **10h** (horário do servidor n8n), o workflow:

1. Lê uma lista de domínios + portas de uma planilha do Google Sheets.
2. Conecta via TLS em cada domínio e inspeciona o certificado.
3. Calcula quantos dias faltam até o vencimento.
4. Detecta **mismatch** (quando o certificado não cobre o hostname consultado, incluindo validação de wildcards).
5. Se algum domínio atingir **exatamente** 15, 10, 5 ou 1 dia restante — ou já estiver **vencido** — dispara uma notificação única no WhatsApp listando **todos** os domínios em zona de alerta (≤ 15 dias).

Se nenhum domínio atingir os marcos no dia, nada é enviado — sem spam diário.

## Diagrama do fluxo

```
┌──────────────────┐     ┌──────────────┐     ┌─────────────┐
│ Schedule Trigger │────▶│ Get List SSL │────▶│ SSL Checker │
│     (10h)        │     │ (Sheets)     │     │   (Code)    │
└──────────────────┘     └──────────────┘     └──────┬──────┘
                                                     │
                                                     ▼
┌──────────────────┐     ┌──────┐     ┌────────────────────┐
│    Send MSG      │◀────│  If  │◀────│       Filter       │
│   (UazAPI)       │ T   │      │     │       (Code)       │
└──────────────────┘     └──┬───┘     └────────────────────┘
                            │ F
                            ▼
                  ┌───────────────────┐
                  │ No Operation      │
                  └───────────────────┘
```

## Como funciona

### Nó `SSL Checker` (JavaScript)

Usa o módulo nativo `tls` do Node.js. Para cada domínio:

- Normaliza o hostname (remove `https://`, paths, espaços).
- Trata IPs e hostnames diferenciadamente (SNI não é enviado para IPs).
- Abre conexão TLS com `rejectUnauthorized: false` (para conseguir inspecionar certs expirados/inválidos sem o handshake morrer).
- Extrai `valid_to`, `subject.CN` e `subjectaltname` (SANs).
- Valida wildcards corretamente: `*.exemplo.com` cobre `a.exemplo.com` mas **não** `a.b.exemplo.com` nem `exemplo.com`.
- Timeout de 10 segundos por domínio.

### Nó `Filter` (JavaScript)

Separa **gatilho** de **conteúdo**:

- **Gatilho:** só dispara a mensagem se algum cert estiver em 15, 10, 5 ou 1 dia *exatos* (ou vencido). Isso evita mensagens diárias repetidas.
- **Conteúdo:** quando dispara, inclui **todos** os domínios em alerta (≤ 15 dias), ordenados por urgência.

Severidade visual:

| Emoji | Condição |
|:-----:|----------|
| 🔀 | Mismatch (cert não cobre o hostname) |
| 🔴 | Vencido |
| 🚨 | ≤ 5 dias |
| ⚠️ | ≤ 10 dias |
| 📅 | ≤ 15 dias |

## Pré-requisitos

- **n8n** self-hosted ou cloud (versão 1.0+ recomendada).
  - O nó `Code` precisa permitir `require('tls')`. Em self-hosted, defina a variável de ambiente:
    ```
    NODE_FUNCTION_ALLOW_BUILTIN=tls
    ```
  - O n8n Cloud **não permite** módulos built-in no nó Code, então este workflow funciona apenas em **instâncias self-hosted**.
- **Google Account** com acesso ao Google Sheets.
- **Conta UazAPI** ([uazapi.com](https://uazapi.com)) com instância ativa conectada a um número WhatsApp — ou substitua o nó `Send MSG` por outro serviço de sua preferência (Telegram, Slack, Discord, SMTP, etc.).

## Instalação

### 1. Importar o workflow

1. Baixe o arquivo [`n8n_SSL_Certificate_Monitor.json`](./n8n_SSL_Certificate_Monitor.json).
2. No n8n, vá em **Workflows → Import from File** e selecione o JSON.

### 2. Criar a planilha

1. Crie uma nova planilha no Google Sheets.
2. Na primeira linha (cabeçalho), coloque exatamente: `Domínio` na coluna A e `porta` na coluna B.
3. Preencha as linhas seguintes com seus domínios. Veja o [template de exemplo](./examples/lista-ssl-template.csv).
4. Copie o **Document ID** da URL da planilha. Ex: em `https://docs.google.com/spreadsheets/d/`**`1abc...xyz`**`/edit`, o ID é `1abc...xyz`.

### 3. Configurar credencial do Google Sheets

1. No n8n, vá em **Credentials → New → Google Sheets OAuth2 API**.
2. Siga o wizard de autorização do Google.
3. Abra o nó `Get List SSL` no workflow e selecione a credencial criada.
4. No campo `Document`, use o seletor (modo "List") e escolha sua planilha — ou cole o Document ID manualmente substituindo `REPLACE_WITH_YOUR_GOOGLE_SHEETS_DOCUMENT_ID`.

### 4. Configurar credencial da UazAPI

1. Na UazAPI, copie o `token` da sua instância.
2. No n8n, vá em **Credentials → New → Header Auth**.
3. Configure:
   - **Name:** `token` (exatamente em minúsculo)
   - **Value:** cole o token da UazAPI
4. Abra o nó `Send MSG` e selecione a credencial criada.

### 5. Ajustar URL e número de destino

No nó `Send MSG`:

- Troque `YOUR_UAZAPI_INSTANCE.uazapi.com` pelo subdomínio da sua instância UazAPI.
- Troque o valor do parâmetro `number` (`55XXXXXXXXXXX`) pelo número de destino no formato internacional sem `+`, espaços ou traços (ex.: `5511999998888` para um celular brasileiro de São Paulo).

### 6. Ativar

1. Teste executando o workflow manualmente (botão **Execute workflow**).
   - ⚠️ Antes de testar, **desafixe o pinData** do nó `Get List SSL` (clique direito → **Unpin data**), senão ele usará os 3 domínios de exemplo em vez da sua planilha.
2. Se tudo funcionar, ative o workflow no toggle superior direito.

## Estrutura da planilha

A planilha deve ter exatamente duas colunas (o cabeçalho precisa bater, o código aceita variações de acento em `Domínio`/`Dominio`):

| Domínio | porta |
|---------|-------|
| example.com | 443 |
| api.example.com | 443 |
| admin.example.com | 8443 |
| streaming.example.com | 19888 |

Regras:

- **Domínio:** aceita com ou sem `https://`, com ou sem path — o código normaliza. IPs também funcionam (mas sem validação de SNI/mismatch).
- **porta:** se vazia ou inválida, assume `443`. Aceita 1 a 65535.

Um [CSV de exemplo](./examples/lista-ssl-template.csv) está incluído — importe-o diretamente no Google Sheets via **Arquivo → Importar**.

## Exemplo de alerta

```
🔐 *Alerta SSL*
🕐 23/04/2026 10:00:15
📋 3 domínio(s) em alerta
🔴 Vencidos: 1 | 🚨 Críticos ≤5d: 1 | 📅 Aviso ≤15d: 1
────────────────────────────────

🔴 *old.example.com* (443)
   Status  : Expirado
   Validade: 20/04/2026
   Faltam  : vencido há 3 dia(s)

🚨 *api.example.com* (443)
   Status  : Válido
   Validade: 28/04/2026
   Faltam  : 5 dia(s)

📅 *streaming.example.com* ⚡ porta 19888
   Status  : Válido
   Validade: 08/05/2026
   Faltam  : 15 dia(s)
```

## Personalização

### Mudar o horário do disparo

No nó `Schedule Trigger`, altere `triggerAtHour` (0–23). Para disparar múltiplas vezes ao dia ou em dias específicos, troque a regra por `cronExpression`.

### Mudar os marcos de alerta

No nó `Filter`, altere a linha:

```js
const MARCOS = new Set([15, 10, 5, 1]);
```

Por exemplo, para alertar em 30, 20, 7 e 1 dia: `new Set([30, 20, 7, 1])`.

### Mudar a zona de "conteúdo"

Por padrão, quando o gatilho dispara a mensagem inclui todos os certs com `daysLeft ≤ 15`. Para mudar esse limite, ajuste o `.filter()` logo após `const emAlerta`:

```js
.filter(r => r.daysLeft !== null && r.daysLeft !== undefined && r.daysLeft <= 15)
```

### Trocar WhatsApp por outro canal

Substitua o nó `Send MSG` por Telegram, Slack, Discord, E-mail (SMTP), Microsoft Teams, etc. A variável `{{ $json.message }}` já vem formatada e pode ser reutilizada em qualquer canal baseado em texto.

### Adicionar error workflow

Em **Settings → Error Workflow**, aponte para um workflow que trate falhas (ex.: registre no Sentry, notifique um canal de operações). O arquivo original usava um error workflow específico da instância, removido na sanitização.

## Troubleshooting

<details>
<summary><strong>O nó SSL Checker retorna <code>Cannot find module 'tls'</code></strong></summary>

Sua instância n8n está bloqueando módulos built-in. Adicione a variável de ambiente `NODE_FUNCTION_ALLOW_BUILTIN=tls` e reinicie o n8n. No n8n Cloud isso não é possível — use self-hosted.
</details>

<details>
<summary><strong>Todos os certs aparecem com <code>status: Timeout</code></strong></summary>

A instância n8n não tem saída para a porta do domínio (firewall, container isolado, etc.). Teste de dentro do container: `openssl s_client -connect dominio.com:443 -servername dominio.com`.
</details>

<details>
<summary><strong>Cert aparece com <code>mismatch: true</code> mas eu acho que está certo</strong></summary>

Verifique o CN e os SANs do certificado com:

```bash
openssl s_client -connect dominio.com:443 -servername dominio.com < /dev/null 2>/dev/null \
  | openssl x509 -noout -text | grep -E "Subject:|DNS:"
```

Um wildcard `*.exemplo.com` **não** cobre `exemplo.com` (precisa estar explicitamente nos SANs).
</details>

<details>
<summary><strong>Recebo mensagem todo dia mesmo sem ter marco de 15/10/5/1</strong></summary>

Provavelmente há certs **vencidos** (`daysLeft ≤ 0`) na planilha — eles disparam todo dia até serem renovados ou removidos da lista. Esse é o comportamento intencional.
</details>

<details>
<summary><strong>Não recebo mensagem apesar de ter cert vencendo em 10 dias</strong></summary>

O gatilho é por **dia exato**. Se o cert vence em 11 dias, não dispara — só no dia em que ele estiver a 10 dias exatos. Se preferir disparos contínuos dentro de uma janela, remova a lógica de marcos e use apenas `daysLeft <= 15`.
</details>

## Contribuição

Contribuições são bem-vindas. Abra uma [issue](../../issues) para reportar bugs ou sugerir melhorias, ou mande um pull request.

Ideias de melhorias:

- Suporte a múltiplos canais de notificação em paralelo.
- Persistência do estado para evitar disparos duplicados se o workflow rodar mais de uma vez no mesmo dia.
- Export de métricas para Prometheus/Grafana.
- Validação OCSP/CRL (certificado revogado).

## Licença

[MIT](./LICENSE) — use, modifique e distribua à vontade.

---

<a id="-english-version"></a>
<a id="english-version"></a>

## 🇺🇸 English version

[🇧🇷 Português](#n8n-ssl-certificate-monitor) | **🇺🇸 English**

An [n8n](https://n8n.io) workflow that performs daily SSL/TLS certificate validity checks and sends WhatsApp alerts (via UazAPI) when a certificate is about to expire or has already expired.

<img width="1166" height="628" alt="Captura de Tela 2026-04-23 às 19 47 42" src="https://github.com/user-attachments/assets/0aaf99c0-4749-4508-b6f9-194cdf5d83d7" />


### Table of contents

- [What it does](#what-it-does)
- [Flow diagram](#flow-diagram)
- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Installation](#installation)
- [Spreadsheet structure](#spreadsheet-structure)
- [Alert example](#alert-example)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting-en)
- [Contributing](#contributing-en)
- [License](#license-en)

### What it does

Every day at **10 AM** (n8n server time), the workflow:

1. Reads a list of domains + ports from a Google Sheets spreadsheet.
2. Connects via TLS to each domain and inspects the certificate.
3. Calculates how many days are left until expiration.
4. Detects **mismatch** (when the certificate does not cover the hostname being queried, including wildcard validation).
5. If any domain hits **exactly** 15, 10, 5, or 1 day remaining — or is already **expired** — it fires a single WhatsApp notification listing **all** domains in the alert zone (≤ 15 days).

If no domain hits any of the thresholds on a given day, nothing is sent — no daily spam.

### Flow diagram

```
┌──────────────────┐     ┌──────────────┐     ┌─────────────┐
│ Schedule Trigger │────▶│ Get List SSL │────▶│ SSL Checker │
│     (10 AM)      │     │ (Sheets)     │     │   (Code)    │
└──────────────────┘     └──────────────┘     └──────┬──────┘
                                                     │
                                                     ▼
┌──────────────────┐     ┌──────┐     ┌────────────────────┐
│    Send MSG      │◀────│  If  │◀────│       Filter       │
│    (UazAPI)      │ T   │      │     │       (Code)       │
└──────────────────┘     └──┬───┘     └────────────────────┘
                            │ F
                            ▼
                  ┌───────────────────┐
                  │ No Operation      │
                  └───────────────────┘
```

### How it works

#### `SSL Checker` node (JavaScript)

Uses Node.js's native `tls` module. For each domain:

- Normalizes the hostname (strips `https://`, paths, whitespace).
- Handles IPs and hostnames differently (SNI is not sent to IPs).
- Opens a TLS connection with `rejectUnauthorized: false` (so the handshake still completes on expired/invalid certs and we can inspect them).
- Extracts `valid_to`, `subject.CN`, and `subjectaltname` (SANs).
- Validates wildcards correctly: `*.example.com` covers `a.example.com` but **not** `a.b.example.com` nor `example.com`.
- 10-second timeout per domain.

#### `Filter` node (JavaScript)

Separates **trigger** from **content**:

- **Trigger:** only fires the message if some cert is at exactly 15, 10, 5, or 1 day remaining (or already expired). This prevents repeated daily messages.
- **Content:** when it fires, includes **all** domains in the alert zone (≤ 15 days), sorted by urgency.

Visual severity:

| Emoji | Condition |
|:-----:|-----------|
| 🔀 | Mismatch (cert does not cover the hostname) |
| 🔴 | Expired |
| 🚨 | ≤ 5 days |
| ⚠️ | ≤ 10 days |
| 📅 | ≤ 15 days |

### Requirements

- **n8n** self-hosted or cloud (version 1.0+ recommended).
  - The `Code` node needs to allow `require('tls')`. On self-hosted, set the environment variable:
    ```
    NODE_FUNCTION_ALLOW_BUILTIN=tls
    ```
  - n8n Cloud **does not allow** built-in modules in the Code node, so this workflow only works on **self-hosted instances**.
- **Google Account** with access to Google Sheets.
- **UazAPI account** ([uazapi.com](https://uazapi.com)) with an active instance connected to a WhatsApp number — or replace the `Send MSG` node with another service of your choice (Telegram, Slack, Discord, SMTP, etc.).

### Installation

#### 1. Import the workflow

1. Download [`n8n_SSL_Certificate_Monitor.json`](./n8n_SSL_Certificate_Monitor.json).
2. In n8n, go to **Workflows → Import from File** and select the JSON.

#### 2. Create the spreadsheet

1. Create a new Google Sheets spreadsheet.
2. On the first row (header), add exactly: `Domínio` in column A and `porta` in column B. (The column names are in Portuguese because the code matches those headers — if you change them, also update the code.)
3. Fill in the following rows with your domains. See the [example template](./examples/lista-ssl-template.csv).
4. Copy the **Document ID** from the spreadsheet URL. For example, in `https://docs.google.com/spreadsheets/d/`**`1abc...xyz`**`/edit`, the ID is `1abc...xyz`.

#### 3. Configure Google Sheets credential

1. In n8n, go to **Credentials → New → Google Sheets OAuth2 API**.
2. Follow the Google authorization wizard.
3. Open the `Get List SSL` node in the workflow and select the credential you created.
4. In the `Document` field, use the "List" mode selector and pick your spreadsheet — or paste the Document ID manually, replacing `REPLACE_WITH_YOUR_GOOGLE_SHEETS_DOCUMENT_ID`.

#### 4. Configure UazAPI credential

1. On UazAPI, copy the `token` from your instance.
2. In n8n, go to **Credentials → New → Header Auth**.
3. Configure:
   - **Name:** `token` (exactly lowercase)
   - **Value:** paste the UazAPI token
4. Open the `Send MSG` node and select the credential you created.

#### 5. Adjust URL and destination number

In the `Send MSG` node:

- Replace `YOUR_UAZAPI_INSTANCE.uazapi.com` with your UazAPI instance subdomain.
- Replace the `number` parameter value (`55XXXXXXXXXXX`) with the destination number in international format without `+`, spaces or dashes (e.g., `15551234567` for a US number, `5511999998888` for a Brazilian São Paulo mobile).

#### 6. Activate

1. Test by running the workflow manually (**Execute workflow** button).
   - ⚠️ Before testing, **unpin the pinData** on the `Get List SSL` node (right-click → **Unpin data**), otherwise it will use the 3 example domains instead of your spreadsheet.
2. If everything works, activate the workflow using the toggle in the top right.

### Spreadsheet structure

The spreadsheet must have exactly two columns (the header must match — the code accepts both `Domínio` and `Dominio`):

| Domínio | porta |
|---------|-------|
| example.com | 443 |
| api.example.com | 443 |
| admin.example.com | 8443 |
| streaming.example.com | 19888 |

Rules:

- **Domínio:** accepts values with or without `https://`, with or without paths — the code normalizes them. IPs also work (but without SNI/mismatch validation).
- **porta:** if empty or invalid, defaults to `443`. Accepts 1 to 65535.

An [example CSV](./examples/lista-ssl-template.csv) is included — import it directly into Google Sheets via **File → Import**.

### Alert example

```
🔐 *Alerta SSL*
🕐 04/23/2026 10:00:15
📋 3 domínio(s) em alerta
🔴 Vencidos: 1 | 🚨 Críticos ≤5d: 1 | 📅 Aviso ≤15d: 1
────────────────────────────────

🔴 *old.example.com* (443)
   Status  : Expirado
   Validade: 04/20/2026
   Faltam  : vencido há 3 dia(s)

🚨 *api.example.com* (443)
   Status  : Válido
   Validade: 04/28/2026
   Faltam  : 5 dia(s)

📅 *streaming.example.com* ⚡ porta 19888
   Status  : Válido
   Validade: 05/08/2026
   Faltam  : 15 dia(s)
```

> Note: alert strings are in Portuguese by default. To translate them, edit the `Filter` Code node.

### Customization

#### Change the trigger time

On the `Schedule Trigger` node, change `triggerAtHour` (0–23). To fire multiple times a day or on specific days, replace the rule with a `cronExpression`.

#### Change the alert thresholds

In the `Filter` node, modify the line:

```js
const MARCOS = new Set([15, 10, 5, 1]);
```

For example, to alert at 30, 20, 7 and 1 days: `new Set([30, 20, 7, 1])`.

#### Change the "content" window

By default, when the trigger fires the message includes all certs with `daysLeft ≤ 15`. To change that limit, adjust the `.filter()` right after `const emAlerta`:

```js
.filter(r => r.daysLeft !== null && r.daysLeft !== undefined && r.daysLeft <= 15)
```

#### Swap WhatsApp for another channel

Replace the `Send MSG` node with Telegram, Slack, Discord, Email (SMTP), Microsoft Teams, etc. The `{{ $json.message }}` variable is already formatted and can be reused on any text-based channel.

#### Add an error workflow

In **Settings → Error Workflow**, point to a workflow that handles failures (e.g., log to Sentry, notify an ops channel). The original file referenced an instance-specific error workflow, which was removed during sanitization.

<a id="troubleshooting-en"></a>
### Troubleshooting

<details>
<summary><strong>The SSL Checker node returns <code>Cannot find module 'tls'</code></strong></summary>

Your n8n instance is blocking built-in modules. Add the environment variable `NODE_FUNCTION_ALLOW_BUILTIN=tls` and restart n8n. This isn't possible on n8n Cloud — use self-hosted.
</details>

<details>
<summary><strong>All certs show <code>status: Timeout</code></strong></summary>

The n8n instance has no network egress to the domain's port (firewall, isolated container, etc.). Test from inside the container: `openssl s_client -connect domain.com:443 -servername domain.com`.
</details>

<details>
<summary><strong>A cert shows <code>mismatch: true</code> but I think it's correct</strong></summary>

Inspect the certificate's CN and SANs with:

```bash
openssl s_client -connect domain.com:443 -servername domain.com < /dev/null 2>/dev/null \
  | openssl x509 -noout -text | grep -E "Subject:|DNS:"
```

A wildcard `*.example.com` does **not** cover `example.com` (it must be explicitly listed in the SANs).
</details>

<details>
<summary><strong>I get a message every day even without any 15/10/5/1 threshold hits</strong></summary>

There are probably **expired** certs (`daysLeft ≤ 0`) in the spreadsheet — they trigger every day until they're renewed or removed from the list. This is intentional behavior.
</details>

<details>
<summary><strong>I don't get a message even though a cert expires in 10 days</strong></summary>

The trigger is by **exact day**. If the cert expires in 11 days, it won't fire — it'll only fire on the day it's exactly at 10 days left. If you prefer continuous alerts within a window, remove the threshold logic and use just `daysLeft <= 15`.
</details>

<a id="contributing-en"></a>
### Contributing

Contributions are welcome. Open an [issue](../../issues) to report bugs or suggest improvements, or send a pull request. See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

Ideas for improvements:

- Support multiple notification channels in parallel.
- State persistence to avoid duplicate alerts if the workflow runs more than once a day.
- Export metrics to Prometheus/Grafana.
- OCSP/CRL validation (revoked certificate check).

<a id="license-en"></a>
### License

[MIT](./LICENSE) — use, modify, and distribute freely.
