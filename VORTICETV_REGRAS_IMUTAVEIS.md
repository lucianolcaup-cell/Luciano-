# VórticeTv — Regras Imutáveis da Baseline

Estas regras só podem ser alteradas por solicitação explícita do proprietário do projeto.

1. Nunca sobrescrever a versão estável/aprovada. Toda evolução parte de cópia/branch.
2. Vídeos usam stream de mídia direto; não retornar ao player web do YouTube com inserção publicitária.
3. O início do vídeo não pode sofrer reinicializações artificiais para bloquear anúncios. SponsorBlock só pode atuar em sponsor/selfpromo com salto seguro em buffer.
4. Vórtice Music permanece áudio-only, sem SponsorBlock e sem watchdog de frame de vídeo. Reprodução deve ser contínua e a fila do álbum avança automaticamente.
5. Não substituir o DefaultLoadControl oficial do Media3 por wrappers/delegação customizada. O crash corrigido na v0.1.10 não pode regressar.
6. Qualidade padrão: 1080p. 1440p/2160p devem aparecer somente quando o extractor expuser stream reproduzível. Escolha manual é autoritativa e não pode ser reduzida silenciosamente.
7. Quando existir faixa de áudio pt-BR/Português, ela deve ser preferida automaticamente para vídeo; o usuário não deve precisar selecionar manualmente.
8. Busca em Português deve priorizar conteúdo em Português/pt-BR sem tornar a pesquisa lenta; fallback para a consulta original é obrigatório.
9. Troca Music <-> Vídeo/Filme deve interromper imediatamente o stream anterior e priorizar o conteúdo novo, evitando concorrência de rede/buffer.
10. Filmes: paginação progressiva; ao selecionar um filme, a paginação perde prioridade imediatamente.
11. Buscar: ao reentrar na aba, campo e resultados da pesquisa anterior ficam zerados; histórico salvo pode permanecer.
12. Canais Abertos: somente fontes oficiais/públicas; live real tem prioridade sobre gravação; nenhuma lista IPTV não autorizada.
13. Sem integração Globo/Globoplay nesta baseline.
14. Popular Brasil deve usar os sinais de tendência disponíveis/localizados para BR; não fingir um ranking geral oficial inexistente.
15. Nenhuma atualização é aprovada sem: checks estáticos, testes Gradle/Kotlin, build Android, verificação de assinatura/artefato e smoke test em Android sem FATAL EXCEPTION.
16. Manter o aplicativo leve: sem novos serviços residentes, sem pools ilimitados de threads e sem bibliotecas adicionais sem necessidade técnica comprovada.
