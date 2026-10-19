Nesta pasta vamos desenvolver um aplicativo de Estudos Bíblicos Dirigidos.

## Seed inicial

Defina `SEED_PASSWORD` no ambiente antes de executar `python -m gsi_ebd.data.seed`.
Sem a variável, ou com valor vazio, o seed aborta antes de acessar o banco.
Todos os usuários novos, incluindo o administrador, devem trocar a senha no
primeiro acesso. Usuários existentes são preservados; sua rotação é manual.
Nunca versione nem compartilhe o valor da variável.
