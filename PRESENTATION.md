# PRESENTATION.md — Roteiro de Apresentação

Roteiro de 10-15 minutos para demonstrar o **Sistema de Gestão de Atendimento Jurídico (NPJ-ITES)**.

---

## 1. Abertura (1 min)

**Problema.** O Núcleo de Práticas Jurídicas do ITES gerencia atendimentos com planilhas, e-mails e cadernos. Isso causa perda de informação entre triagem e acompanhamento, dificuldade de orientação por parte dos professores e falta de controle sobre prazos e documentos pendentes.

**Solução.** Plataforma web que centraliza assistidos, atendimentos, triagem, documentos, orientação e agenda — com visão diferenciada para aluno, professor e coordenação.

**Stack.**
- Frontend: Next.js + React + TypeScript + Tailwind (Vercel)
- Backend: Python + FastAPI (Render)
- Banco + Auth + Storage: Supabase (PostgreSQL)

---

## 2. Demonstração (10 min)

### 2.1. Login e navegação (1 min)

- Abrir `https://nucleo-juridico-frontend.vercel.app/login`
- Mostrar visual NPJ-ITES (logo, identidade, tabs Entrar/Cadastrar)
- Login como **admin** (`admin@ites.edu.br` / `Admin@1234`)
- Sidebar com todos os itens — admin vê **Administração** e **Casos para Análise**

### 2.2. Dashboard do admin (1 min)

- 4 cards de KPI no topo
- Gráficos: por status, por área jurídica
- Listas de pendências (aguardando docs, em análise)
- Falar: "Cada perfil vê uma visão diferente."

### 2.3. Cadastro de cliente (1 min)

- `/clientes/novo`
- Demonstrar validação de CPF (digitar `11111111111` → "CPF inválido")
- Digitar CPF válido com máscara live
- Salvar → tela de detalhes com tabs e histórico já populado

### 2.4. Abertura de atendimento (1 min)

- `/atendimentos/novo`
- Combobox de cliente com busca por nome ou CPF
- Selecionar área → tipos de demanda filtrados dinamicamente
- Marcar urgência, adicionar descrição
- Salvar

### 2.5. Triagem (1 min)

- Aba "Triagem" no atendimento
- Preencher relato do cliente, marcar urgência → aparece banner de alerta vermelho
- Listar documentos pendentes → aparece banner amber
- **3 botões**: Salvar rascunho / Salvar triagem / Encaminhar ao professor

### 2.6. Anexar documento (1 min)

- Aba "Documentos" → "Anexar documento"
- Selecionar PDF, tipo, observação → upload
- Documento aparece com status "Entregue"
- Mostrar que o link é signed URL (curto, expira em 1h) — bucket privado

### 2.7. Encaminhar ao professor (30s)

- Botão "Encaminhar ao professor" → status muda para "Encaminhado ao professor"
- Histórico atualiza no Timeline

### 2.8. Análise do professor (2 min)

- **Logout e login como professor** (`professor@ites.edu.br`)
- Sidebar mostra **Casos para Análise**
- `/casos-analise` → caso aparece na fila
- Clicar "Analisar" → tela única consolidada (cliente + atendimento + triagem + documentos + histórico + orientações)
- Escrever orientação jurídica
- Escolher decisão (4 opções em radio cards)
- **Confirmar decisão** → status muda automaticamente

### 2.9. Agenda (1 min)

- Logout, login de novo como admin
- `/agenda` → toggle **Lista / Calendário**
- Mostrar calendário mensal com pontos coloridos
- Clicar em um dia → drawer com os retornos
- Novo retorno → vinculado ao atendimento → evento entra no histórico do atendimento

### 2.10. Administração (1 min)

- `/administracao` → 3 cards
- `/admin/usuarios` → criar um aluno novo
- `/admin/areas-juridicas` → mostrar criar/desativar
- `/admin/tipos-demanda` → mostrar associação com área

### 2.11. Histórico e auditoria (30s)

- Voltar no atendimento criado → aba **Histórico**
- Timeline mostra: "Atendimento aberto por Coordenação NPJ", "Documento anexado", "Encaminhado ao professor", "Status alterado de Em triagem para Encaminhado ao professor", "Orientação registrada com decisão Aprovar encaminhamento"
- Sublinhar: **append-only**, sem possibilidade de edição pelo frontend

---

## 3. Arquitetura (2 min)

```
┌─────────────────┐         ┌─────────────────┐
│  Vercel (Next)  │ ──HTTP──┤  Render (API)   │
│  React 19 + TS  │  Bearer │  FastAPI        │
└─────────────────┘         └────────┬────────┘
                                     │
                            ┌────────┴────────┐
                            │   Supabase      │
                            │ ┌─────────────┐ │
                            │ │ PostgreSQL  │ │
                            │ ├─────────────┤ │
                            │ │ Auth (JWT)  │ │
                            │ ├─────────────┤ │
                            │ │ Storage     │ │
                            │ └─────────────┘ │
                            └─────────────────┘
```

- **Frontend** consome só a API REST (não bate direto no Supabase).
- **Backend** valida JWT do Supabase, valida payloads com Pydantic, aplica escopo por perfil em todas as queries.
- **Storage privado** — backend gera signed URLs sob demanda; nenhum arquivo é acessível publicamente.
- **Histórico granular** — toda ação relevante grava evento em `attendance_history` (append-only).

---

## 4. Segurança e qualidade (1 min)

- ✅ Validação real de CPF (dígitos verificadores) frontend + backend
- ✅ JWT validado com chave assimétrica (ES256) via JWKS — sem segredo compartilhado
- ✅ Bucket de documentos privado + signed URLs de 1h
- ✅ Escopo automático: aluno só vê os seus, professor só vê os seus, admin tudo
- ✅ Rotas `/admin/*` com guarda no router (403 para não-admin)
- ✅ Handler global de erro — sem vazamento de stack trace em produção
- ✅ Soft-delete consistente (clientes, atendimentos, documentos, áreas, tipos)
- ✅ Histórico append-only sem endpoints de edição

---

## 5. Métricas do projeto (30s)

- **~30 rotas** no frontend
- **~70 endpoints** no backend
- **10 tabelas** + **8 migrations**
- **~12 módulos** organizados por domínio
- **3 perfis** com escopo automático
- Build de produção em **~10s**

---

## 6. O que vem depois (1 min)

Fora do MVP, planejado para próximas iterações:

- Portal do assistido
- Assinatura eletrônica de documentos
- Integração com tribunais (consulta processual)
- Notificações por e-mail / WhatsApp
- Export real de relatórios (PDF e Excel)
- Recuperação de senha funcional
- Aplicativo mobile

---

## Dicas finais

- **Antes de começar**: faça login pré-apresentação para evitar cold start do Render.
- **Tenha pelo menos 3 atendimentos cadastrados** em estágios diferentes (novo, triagem, encaminhado, analisado).
- **Anexe pelo menos 1 documento** para mostrar o Storage.
- **Crie pelo menos 1 retorno** para o dia atual para o Calendário ficar populado.
- **Use 2 abas do navegador** (uma logada como admin, outra como professor) para acelerar a troca de perfil.
- Se o Render estiver dormindo, abra o `/health` antes da demo para acordar.
