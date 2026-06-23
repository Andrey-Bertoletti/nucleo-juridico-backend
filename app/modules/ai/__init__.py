"""Módulo de Análise com IA (Fase 1).

Análise de documentos do NPJ por meio de ações fechadas (resumo, prazos,
partes, etc.) e relatório geral por cliente. O provedor de IA é desacoplado
(ver `providers/`), permitindo trocar entre API externa e modelo local sem
alterar a lógica de negócio.
"""
