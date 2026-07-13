from controllers.AppController import AppController
from views.MainWindow import MainWindow

if __name__ == "__main__":
    controller = AppController()
    app = MainWindow(controller=controller)
    app.mainloop()