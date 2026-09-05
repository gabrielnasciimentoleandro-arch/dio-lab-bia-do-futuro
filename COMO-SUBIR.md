# Como levar o projeto para o seu fork

Você já fez o fork — ele está em
`https://github.com/SEU-USUARIO/dio-lab-bia-do-futuro`, ainda com o conteúdo
original do template.

Falta trazer o projeto para a sua máquina e enviar. São 10 minutos.

---

## Passo 1 — Baixar o projeto

Baixe **`luma-projeto.zip`** (está na raiz do workspace, ao lado da pasta do
projeto) e descompacte onde preferir. Vai criar a pasta
`assistente-financeiro/`.

O zip inclui o histórico completo de commits.

---

## Passo 2 — Abrir o terminal na pasta

**Windows:** abra a pasta `assistente-financeiro` no Explorer, clique na barra
de endereço, digite `cmd` e pressione Enter.

**Mac/Linux:** abra o terminal e use `cd caminho/para/assistente-financeiro`.

Confirme que está no lugar certo:

```bash
git log --oneline
```

Deve listar cerca de 20 commits, do mais recente para o mais antigo.

---

## Passo 3 — Configurar sua identidade

O pacote vem sem configuração de usuário, de propósito (nenhuma credencial
viaja junto). Informe a sua:

```bash
git config user.name "Seu Nome"
git config user.email "seu@email.com"
```

Use o mesmo e-mail da sua conta GitHub, para os commits aparecerem no seu
perfil.

---

## Passo 4 — Ajustar o badge e conferir tudo

```bash
./publicar.sh SEU-USUARIO dio-lab-bia-do-futuro
```

No Windows, se `./publicar.sh` não funcionar, use o Git Bash (vem com o Git) ou
faça à mão: abra o `README.md`, linha 11, e troque `SEU-USUARIO/SEU-REPO` pelo
seu caminho real.

---

## Passo 5 — Conectar ao fork e enviar

```bash
git remote add origin https://github.com/SEU-USUARIO/dio-lab-bia-do-futuro.git
git push --force origin main
```

O GitHub vai pedir login. Se pedir senha, **não é a senha da conta** — é um
Personal Access Token: GitHub > Settings > Developer settings > Personal access
tokens > Tokens (classic) > Generate new token, com o escopo `repo` marcado.

> **Por que `--force`?** O seu histórico e o do template são independentes — não
> têm commits em comum. O force diz ao Git para substituir o conteúdo do fork
> pelo seu. Como o fork acabou de ser criado e só tem os arquivos-modelo, não há
> nada a perder.

---

## Passo 6 — Conferir

Atualize a página do seu fork. Você deve ver:

- O README da Luma, com os badges no topo
- As pastas `src/`, `eval/`, `audio/`, `examples/`
- Cerca de 20 commits no histórico
- Na aba **Actions**, a suíte rodando (autorize se o GitHub pedir)

O badge de CI fica verde alguns minutos depois.

---

## Se algo der errado

**"failed to push some refs"** — faltou o `--force`.

**"remote origin already exists"** — já existe uma origem configurada. Troque
por:

```bash
git remote set-url origin https://github.com/SEU-USUARIO/dio-lab-bia-do-futuro.git
```

**"Authentication failed"** — use o Personal Access Token no lugar da senha.

**Actions não roda** — vá na aba Actions do fork e clique em
*"I understand my workflows, go ahead and enable them"*. O GitHub desativa
workflows em forks por padrão.

---

## Depois de subir

Falta só o vídeo. O roteiro está em `docs/05-pitch.md`, o passo a passo de tela
em `docs/05b-roteiro-gravacao.md`, e o espaço para o link já está preparado no
topo do `README.md` — é um comentário HTML, basta descomentar e colar.
