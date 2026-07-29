# Procedura di rollback

1. sospendere nuove submission dal gateway;
2. attendere o annullare i job non terminali;
3. acquisire backup del database e dei volumi tenant;
4. ripristinare l'immagine applicativa della versione precedente;
5. se necessario, ripristinare il database soltanto in ambiente isolato;
6. verificare schema, tenant, analisi, feedback e readiness;
7. riaprire il traffico dopo health check e smoke test.

Il rollback applicativo non deve eliminare volumi o database. Non usare
`docker compose down -v` durante una procedura di ripristino.
