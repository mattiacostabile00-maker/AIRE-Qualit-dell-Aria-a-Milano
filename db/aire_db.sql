-- ============================================================
--  PROGETTO AIRE — Schema del database
--  Esegui questo file nel SQL Editor di Supabase
--  Settings → SQL Editor → New Query → incolla → Run
-- ============================================================


-- ── 1. TABELLA STAZIONI ────────────────────────────────────
CREATE TABLE IF NOT EXISTS stazioni (
    id   INTEGER PRIMARY KEY,
    nome TEXT    NOT NULL,
    zona TEXT
);

-- Dati di base (le 5 stazioni presenti nel dataset)
INSERT INTO stazioni (id, nome, zona) VALUES
    (2, 'Stazione Pascal',       'Milano Nord-Est'),
    (3, 'Stazione Juvara',       'Milano Centro'),
    (4, 'Stazione Via Marche',   'Milano Nord'),
    (6, 'Stazione Verziere',     'Milano Centro'),
    (7, 'Stazione Senato',       'Milano Centro-Est')
ON CONFLICT (id) DO NOTHING;


-- ── 2. TABELLA RILEVAMENTI ─────────────────────────────────
-- Struttura 1:1 con il CSV originale
-- Un record per ogni misurazione giornaliera per stazione

CREATE TABLE IF NOT EXISTS rilevamenti (
    id          SERIAL  PRIMARY KEY,
    stazione_id INTEGER NOT NULL REFERENCES stazioni(id),
    data        DATE    NOT NULL,
    inquinante  TEXT    NOT NULL,   -- C6H6 | CO_8h | NO2 | O3 | PM10 | PM25 | SO2
    valore      REAL,               -- NULL se dato non disponibile quel giorno
    UNIQUE (stazione_id, data, inquinante)
);

-- Indici per velocizzare le query più comuni
CREATE INDEX IF NOT EXISTS idx_rile_data        ON rilevamenti (data);
CREATE INDEX IF NOT EXISTS idx_rile_inquinante  ON rilevamenti (inquinante);
CREATE INDEX IF NOT EXISTS idx_rile_stazione    ON rilevamenti (stazione_id);


-- ── 3. VISTA COMODA: formato largo ─────────────────────────
-- Ogni riga = un giorno + stazione, ogni inquinante = colonna
-- Usata dal modulo ML per il pivot automatico

CREATE OR REPLACE VIEW v_wide AS
SELECT
    data,
    stazione_id,
    MAX(CASE WHEN inquinante = 'PM10'  THEN valore END) AS pm10,
    MAX(CASE WHEN inquinante = 'PM25'  THEN valore END) AS pm25,
    MAX(CASE WHEN inquinante = 'NO2'   THEN valore END) AS no2,
    MAX(CASE WHEN inquinante = 'O3'    THEN valore END) AS o3,
    MAX(CASE WHEN inquinante = 'C6H6'  THEN valore END) AS c6h6,
    MAX(CASE WHEN inquinante = 'CO_8h' THEN valore END) AS co_8h,
    MAX(CASE WHEN inquinante = 'SO2'   THEN valore END) AS so2
FROM rilevamenti
GROUP BY data, stazione_id;


-- ── 4. QUERY DI VERIFICA ───────────────────────────────────
-- Esegui queste per verificare che tutto sia andato bene

-- Conta le righe caricate:
-- SELECT COUNT(*) FROM rilevamenti;

-- Media per inquinante:
-- SELECT inquinante, ROUND(AVG(valore)::numeric, 2) AS media
-- FROM rilevamenti WHERE valore IS NOT NULL
-- GROUP BY inquinante ORDER BY media DESC;

-- Anteprima vista larga:
-- SELECT * FROM v_wide LIMIT 10;
