DROP TABLE IF EXISTS judgment_principles;
DROP TABLE IF EXISTS judgments;
DROP TABLE IF EXISTS fatwa_principles;
DROP TABLE IF EXISTS fatwas;
DROP TABLE IF EXISTS law_articles;
DROP TABLE IF EXISTS law_promulgation_articles;
DROP TABLE IF EXISTS laws;

-- Judgments
CREATE TABLE judgments (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    court_name VARCHAR(255),
    chamber_type VARCHAR(255),
    appeal_number INT,
    judicial_year INT,
    hearing_date DATE,
    volume_number INT,
    part_number INT,
    page_number INT,
    rule_number INT,
    reference_number INT,
    authority TEXT,
    facts TEXT,
    reasons TEXT
);

CREATE TABLE judgment_principles (
    id SERIAL PRIMARY KEY,
    judgment_id INT REFERENCES judgments(id) ON DELETE CASCADE,
    principle_number INT NOT NULL,
    content TEXT NOT NULL,
    UNIQUE(judgment_id, principle_number)
);

-- Fatwas
CREATE TABLE fatwas (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    fatwa_number INT,
    fatwa_date DATE,
    hearing_date DATE,
    file_number VARCHAR(255),
    authority TEXT,
    topic TEXT,
    facts TEXT,
    application TEXT,
    opinion TEXT
);

CREATE TABLE fatwa_principles (
    id SERIAL PRIMARY KEY,
    fatwa_id INT REFERENCES fatwas(id) ON DELETE CASCADE,
    principle_number INT NOT NULL,
    content TEXT NOT NULL,
    UNIQUE(fatwa_id, principle_number)
);

-- Laws
CREATE TABLE laws (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    law_number INT,
    issue_date DATE,
    publish_date DATE,
    subject TEXT,
    gazette VARCHAR(255)
);

CREATE TABLE law_articles (
    id SERIAL PRIMARY KEY,
    law_id INT REFERENCES laws(id) ON DELETE CASCADE,
    article_number INT NOT NULL,
    is_repeated BOOLEAN DEFAULT FALSE,
    original_text TEXT,
    final_text TEXT NOT NULL,
    final_text_date DATE,
    UNIQUE(law_id, article_number, is_repeated)
);

CREATE TABLE law_promulgation_articles (
    id SERIAL PRIMARY KEY,
    law_id INT REFERENCES laws(id) ON DELETE CASCADE,
    article_number INT NOT NULL,
    original_text TEXT,
    final_text TEXT NOT NULL,
    final_text_date DATE,
    UNIQUE(law_id, article_number)
);

-- Indices on foreign keys for joins
CREATE INDEX idx_judgment_principles_judgment_id
ON judgment_principles(judgment_id);

CREATE INDEX idx_fatwa_principles_fatwa_id
ON fatwa_principles(fatwa_id);

CREATE INDEX idx_law_articles_law_id
ON law_articles(law_id);

CREATE INDEX idx_law_promulgation_articles_law_id
ON law_promulgation_articles(law_id);