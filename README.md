Standards:
  - Extensive logging with backups to file which can be donwloaded within the telegram client.
  - Graceful degradation and no operation-breaking errors. If an error is critical the user should be sent to the main menu and all their chat data should be cleared.
  - Concurrency awareness should be a part of the design wherever possible, especially during IO/SQL operations, where using locks is essential to maintaining security and reducing errors.


Known issues:
  - Deletion of admins with identical names is not handled properly and leads to neither admin getting deleted because the buttons are only differentiated by their names. This currently causes no problems because

Buglist:
  - Commands should be one of the certain ones to return to a safe state for the program. Currently, they can't be called from everywhere

CHANGES TO MAKE:
  - Add a SessionManagerBase as an abstract class to simplify user interactions
    - Make children AdminSessionManager and SessionManager
  - Remove AdminFactory, replace with Password class
    - Password extends RandomSequenceGenerator class
  - Remove Admin, replace with DBSyncedAdmin using CRUD principles
    - Same for questions