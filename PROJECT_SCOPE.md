# PROJECT_SCOPE — Sistema de Gestão de Atendimento Jurídico

Este documento descreve o escopo do **Sistema de Gestão de Atendimento Jurídico** sob a perspectiva do backend. O mesmo documento existe no repositório do frontend e ambos devem ser mantidos sincronizados.

---

## 1. Problema

Núcleos de prática jurídica e pequenos escritórios ainda dependem de planilhas, e-mails e cadernos físicos para gerenciar atendimento de assistidos/clientes. Esse modelo causa:

- Perda de informações entre o atendimento inicial (triagem) e o acompanhamento do caso.
- Dificuldade de orientação por parte dos professores responsáveis sobre os atendimentos conduzidos por estudantes/estagiários.
- Falta de controle sobre prazos, documentos pendentes e andamento de cada caso.
- Inexistência de um histórico unificado por assistido.
- Dificuldade para gerar relatórios e indicadores institucionais.

---

## 2. Objetivo

Oferecer uma plataforma web simples e segura para:

1. Centralizar o cadastro de assistidos e o registro de atendimentos.
2. Apoiar a triagem inicial (área do direito, urgência, encaminhamento).
3. Permitir que professores supervisionem e orientem os casos conduzidos por estudantes/estagiários.
4. Armazenar documentos relacionados ao caso de forma organizada e segura (Supabase Storage).
5. Acompanhar o ciclo de vida de cada caso — do primeiro atendimento ao encerramento.

---

## 3. Perfis de usuário

| Perfil                       | Descrição                                                                                  |
|------------------------------|--------------------------------------------------------------------------------------------|
| **Administrador**            | Configura o núcleo, gerencia usuários e permissões, acompanha indicadores gerais.          |
| **Professor / Supervisor**   | Orienta atendimentos, valida triagens, aprova encaminhamentos e revisa documentos.         |
| **Estudante / Estagiário**   | Realiza o atendimento, registra a triagem, anexa documentos e atualiza o andamento.        |
| **Recepção / Atendente**     | Faz o primeiro contato, cadastra o assistido e abre a ficha de atendimento inicial.        |
| **Assistido / Cliente**      | *(Não acessa o sistema na v1)* — seus dados são geridos internamente.                      |

---

## 4. Funcionalidades da primeira versão (MVP)

### 4.1. Autenticação e gestão de usuários
- Login com e-mail e senha (Supabase Auth).
- Controle de acesso por perfil (Admin, Professor, Estudante, Recepção).
- Cadastro de usuários internos pelo Administrador.

### 4.2. Cadastro de assistidos/clientes
- Dados pessoais básicos (nome, contato, documentos, endereço).
- Histórico unificado por assistido (atendimentos e casos vinculados).

### 4.3. Atendimento e triagem
- Abertura de ficha de atendimento.
- Triagem com classificação por área do direito e urgência.
- Encaminhamento do atendimento para um estudante/estagiário e respectivo professor.

### 4.4. Casos
- Conversão de atendimento triado em caso ativo.
- Status do caso (em andamento, aguardando documentos, encerrado, etc.).
- Linha do tempo com histórico de atualizações.

### 4.5. Documentos
- Upload e organização de documentos por caso (Supabase Storage).
- Tipos básicos (procuração, RG, comprovante, petição, etc.).

### 4.6. Orientação de professores
- Lista de casos sob orientação do professor.
- Espaço para observações/orientações no caso.
- Marcação de pendências (ex.: "documento faltando", "revisar petição").

### 4.7. Painel inicial (Dashboard)
- Indicadores básicos: atendimentos abertos, casos por status, pendências.

---

## 5. Fora do escopo da primeira versão

Os itens abaixo **não** fazem parte do MVP e poderão ser avaliados em versões futuras:

- Portal de acesso para o assistido/cliente.
- Assinatura eletrônica de documentos.
- Integração com tribunais (consulta processual, push de andamento).
- Agenda integrada / sincronização com Google Calendar.
- Faturamento, honorários e controle financeiro.
- Chat interno em tempo real.
- Aplicativo mobile nativo.
- Relatórios avançados / BI customizado.
- Workflow configurável de aprovação (motor de workflow).
- Notificações por WhatsApp / SMS.
- Multi-tenant (vários núcleos no mesmo deploy).

---

## 6. Premissas técnicas

- **Frontend:** Next.js + React + TypeScript + Tailwind CSS.
- **Backend:** Python + FastAPI.
- **Banco:** PostgreSQL gerenciado pelo Supabase.
- **Storage:** Supabase Storage para documentos.
- **Autenticação:** Supabase Auth.
- Comunicação entre front e back via **API REST** com autenticação por token.
