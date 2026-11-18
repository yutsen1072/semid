CREATE TABLE IF NOT EXISTS account ( /*帳號表，儲存使用者基本資料*/
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(80) NOT NULL,
    role VARCHAR(10) NOT NULL CHECK (role IN ('author', 'editor')),
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_session (/*登入憑證表*/
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES account(id),
    token_hash VARCHAR(64) NOT NULL UNIQUE,/*憑證雜湊*/
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS submission ( /*稿件表*/
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT '編輯中',
    author_name VARCHAR(80) NOT NULL DEFAULT '一般作者',
    attachment_filename VARCHAR(255),
    return_reason TEXT,
    owner_id INTEGER REFERENCES account(id),/*關聯到作者*/
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);