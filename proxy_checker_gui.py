import requests
import time
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QTextEdit, QFileDialog
from PyQt6.QtCore import QThread, pyqtSignal, QObject


class Worker(QObject):
    # Signal emitted for each proxy result (as soon as it is available)
    progress = pyqtSignal(str)
    # Signal to indicate that all processing is finished
    finished = pyqtSignal()

    def __init__(self, all_proxies, checkProxy):
        super().__init__()
        self.all_proxies = all_proxies
        self.checkProxy = checkProxy

    def run(self):
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all proxy-check tasks
            futures = {
                executor.submit(self.checkProxy, proxy, ptype): (proxy, ptype)
                for proxy, ptype in self.all_proxies
            }
            # Process each result as it becomes available
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        self.progress.emit(result)
                except Exception as e:
                    self.progress.emit(f"Error: {e}")
        self.finished.emit()


class ProxyCheckerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Proxy Checker")
        self.setGeometry(100, 100, 600, 400)

        # Using a QTextEdit to show multiple lines of output
        self.resultTextEdit = QTextEdit()
        self.resultTextEdit.setReadOnly(True)
        self.loadButton = QPushButton("Load Proxy File")
        self.checkButton = QPushButton("Check Proxies")

        layout = QVBoxLayout()
        layout.addWidget(self.resultTextEdit)
        layout.addWidget(self.loadButton)
        layout.addWidget(self.checkButton)
        self.setLayout(layout)

        self.loadButton.clicked.connect(self.loadFile)
        self.checkButton.clicked.connect(self.checkProxies)
        self.proxyFile = None

    def loadFile(self):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        if file_dialog.exec():
            self.proxyFile = file_dialog.selectedFiles()[0]
            self.resultTextEdit.append(f"Loaded proxy file: {self.proxyFile}")

    def loadProxies(self):
        proxies = {"http": [], "https": [], "socks4": [], "socks5": []}
        with open(self.proxyFile, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if len(row) < 2:
                    continue
                proxy, ptype = row[0], row[1].lower()
                if ptype in proxies:
                    proxies[ptype].append(proxy)
        # Flatten the list of proxies with their type
        all_proxies = [(proxy, ptype) for ptype, proxy_list in proxies.items() for proxy in proxy_list]
        return all_proxies

    def checkProxy(self, proxy, proxy_type):
        # Choose URL based on proxy type (default to HTTP)
        test_url = "http://httpbin.org/ip" if proxy_type != "https" else "https://httpbin.org/ip"
        start_time = time.time()
        try:
            if proxy_type in ["http", "https"]:
                proxies = {"http": f"http://{proxy}", "https": f"https://{proxy}"}
                response = requests.get(test_url, proxies=proxies, timeout=5)
            else:
                # For SOCKS proxies, adjust this as needed
                response = requests.get(test_url, timeout=5)
            if response.status_code == 200:
                ping = round(time.time() - start_time, 2)
                return f"[✔] {proxy_type.upper()} {proxy} - Working (Ping: {ping}s)"
        except Exception:
            return f"[✖] {proxy_type.upper()} {proxy} - Failed"
        return None

    def checkProxies(self):
        if not self.proxyFile:
            self.resultTextEdit.append("Please load a proxy file first.")
            return

        self.resultTextEdit.append("Checking proxies...")
        all_proxies = self.loadProxies()
        if not all_proxies:
            self.resultTextEdit.append("No proxies found in the file.")
            return

        # Set up and start the worker thread
        self.worker_thread = QThread()
        self.worker = Worker(all_proxies, self.checkProxy)
        self.worker.moveToThread(self.worker_thread)

        # Connect progress and finished signals to update the UI
        self.worker.progress.connect(self.updateResults)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(lambda: self.resultTextEdit.append("Finished checking proxies."))
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.start()

    def updateResults(self, result):
        # Append each proxy result as it arrives
        self.resultTextEdit.append(result)


if __name__ == "__main__":
    app = QApplication([])
    window = ProxyCheckerApp()
    window.show()
    app.exec()