-- =============================================================================
-- Peças Processuais — Entrega e correção de peças por alunos
-- =============================================================================

CREATE TABLE IF NOT EXISTS pieces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Quem entregou
    student_id UUID REFERENCES profiles(id) ON DELETE SET NULL,

    -- Vinculação opcional a um atendimento
    attendance_id UUID REFERENCES attendances(id) ON DELETE SET NULL,

    -- Dados da peça
    title VARCHAR(300) NOT NULL,
    description TEXT,

    -- Arquivo (obrigatório no momento da criação)
    file_name TEXT NOT NULL,
    storage_path TEXT NOT NULL,

    -- Status da peça no fluxo de correção
    status TEXT NOT NULL DEFAULT 'entregue'
        CHECK (status IN ('entregue', 'em_correcao', 'corrigida', 'devolvida_para_ajuste')),

    -- Professor que corrigiu
    corrected_by UUID REFERENCES profiles(id) ON DELETE SET NULL,
    correction_notes TEXT,

    -- Observações do aluno
    student_notes TEXT,

    -- Timestamps
    delivered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    corrected_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Índices para consultas frequentes
CREATE INDEX IF NOT EXISTS idx_pieces_student_id   ON pieces(student_id);
CREATE INDEX IF NOT EXISTS idx_pieces_attendance_id ON pieces(attendance_id);
CREATE INDEX IF NOT EXISTS idx_pieces_status        ON pieces(status);
CREATE INDEX IF NOT EXISTS idx_pieces_delivered_at  ON pieces(delivered_at DESC);

-- Trigger para atualizar updated_at automaticamente
CREATE TRIGGER set_pieces_updated_at
    BEFORE UPDATE ON pieces
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
