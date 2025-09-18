CREATE TABLE IF NOT EXISTS hello_lab (
  id SERIAL PRIMARY KEY,
  msg TEXT NOT NULL
);
INSERT INTO hello_lab (msg) VALUES ('docker-lab1 ready');
