Standards:
  - Extensive logging with backups to file which can be donwloaded within the telegram client.
  - Graceful degradation and no operation-breaking errors. If an error is critical the user should be sent to the main menu and all their chat data should be cleared.
  - Concurrency awareness should be a part of the design wherever possible, especially during IO/SQL operations, where using locks is essential to maintaining security and reducing errors.
