"""
Migração: preferências por MODALIDADE (tipo de escala) + fator de limite.
- Adiciona schedule_type_id em user_preferences e preference_factor em balance_configs.
- Troca a unique constraint para incluir o tipo.
- Limpa as preferências antigas (modelo por-dia, sem tipo).

Execute uma vez: python -m app.migrate_preferences
"""
from sqlalchemy import text
from app.core.database import engine


def run():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS schedule_type_id VARCHAR(36)"))
        conn.execute(text("ALTER TABLE balance_configs ADD COLUMN IF NOT EXISTS preference_factor INTEGER NOT NULL DEFAULT 2"))
        # Limpa preferências antigas (sem modalidade) e ajusta a unique constraint
        conn.execute(text("DELETE FROM user_preferences"))
        conn.execute(text("ALTER TABLE user_preferences DROP CONSTRAINT IF EXISTS uq_user_preference"))
        conn.execute(text(
            "ALTER TABLE user_preferences ADD CONSTRAINT uq_user_preference "
            "UNIQUE (user_id, year, month, date, schedule_type_id, type)"
        ))
        # FK para schedule_types (ignora se já existir)
        conn.execute(text(
            "DO $$ BEGIN "
            "ALTER TABLE user_preferences ADD CONSTRAINT fk_pref_type "
            "FOREIGN KEY (schedule_type_id) REFERENCES schedule_types(id); "
            "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
        ))
    print("Migração de preferências concluída.")


if __name__ == "__main__":
    run()
