from PyQt5.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from application.team_app import team_app


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("서버 로그인")
        self.resize(420, 220)
        self.current_user = None
        self.needs_bootstrap = False
        self._create_ui()
        self.refresh_setup_status()

    def _create_ui(self):
        layout = QVBoxLayout()

        guide = QLabel(
            "FastAPI 서버에 로그인한 뒤 클라이언트를 사용할 수 있습니다.\n"
            "서버에 계정이 아직 없을 때만 최초 관리자 생성을 사용할 수 있습니다."
        )
        self.guide_label = guide
        guide.setWordWrap(True)

        form = QFormLayout()
        self.server_url_input = QLineEdit()
        self.server_url_input.setText(team_app.load_server_base_url())
        self.username_input = QLineEdit()
        self.username_input.setText(team_app.load_auth_username())
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        form.addRow("서버 주소", self.server_url_input)
        form.addRow("아이디", self.username_input)
        form.addRow("비밀번호", self.password_input)

        button_row = QHBoxLayout()
        self.bootstrap_btn = QPushButton("최초 관리자 생성")
        self.login_btn = QPushButton("로그인")
        self.cancel_btn = QPushButton("종료")
        button_row.addWidget(self.bootstrap_btn)
        button_row.addWidget(self.login_btn)
        button_row.addWidget(self.cancel_btn)

        layout.addWidget(guide)
        layout.addLayout(form)
        layout.addLayout(button_row)
        self.setLayout(layout)

        self.bootstrap_btn.clicked.connect(self.bootstrap_admin)
        self.login_btn.clicked.connect(self.login)
        self.cancel_btn.clicked.connect(self.reject)
        self.password_input.returnPressed.connect(self.login)

    def refresh_setup_status(self):
        team_app.save_server_base_url(self.server_url_input.text().strip())
        try:
            result = team_app.get_auth_setup_status()
            self.needs_bootstrap = bool(result.get("needs_bootstrap"))
        except Exception:
            self.needs_bootstrap = False

        self.bootstrap_btn.setVisible(self.needs_bootstrap)
        if self.needs_bootstrap:
            self.guide_label.setText(
                "FastAPI 서버에 로그인한 뒤 클라이언트를 사용할 수 있습니다.\n"
                "현재 서버에는 계정이 없어서 최초 관리자 생성을 사용할 수 있습니다."
            )
        else:
            self.guide_label.setText(
                "FastAPI 서버에 로그인한 뒤 클라이언트를 사용할 수 있습니다.\n"
                ##"이미 서버 계정이 존재하므로 일반 로그인만 사용하면 됩니다."
            )

    def login(self):
        username, password = self._read_credentials()
        if not username or not password:
            return

        team_app.save_server_base_url(self.server_url_input.text().strip())

        try:
            result = team_app.login(username, password)
        except Exception as exc:
            QMessageBox.critical(self, "로그인 실패", str(exc))
            return

        self._accept_auth_result(result, username)

    def bootstrap_admin(self):
        username, password = self._read_credentials()
        if not username or not password:
            return

        team_app.save_server_base_url(self.server_url_input.text().strip())

        try:
            result = team_app.bootstrap_admin(username, password)
        except Exception as exc:
            QMessageBox.critical(self, "최초 관리자 생성 실패", str(exc))
            return

        self._accept_auth_result(result, username)
        QMessageBox.information(self, "완료", "최초 관리자 계정 생성과 로그인이 완료되었습니다.")

    def _read_credentials(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not self.server_url_input.text().strip():
            QMessageBox.warning(self, "입력 오류", "서버 주소를 입력해주세요.")
            return None, None
        if not username:
            QMessageBox.warning(self, "입력 오류", "아이디를 입력해주세요.")
            return None, None
        if not password:
            QMessageBox.warning(self, "입력 오류", "비밀번호를 입력해주세요.")
            return None, None
        return username, password

    def _accept_auth_result(self, result, username):
        # access_token 은 서버가 서명한 JWT 이다.
        # 클라이언트는 이 문자열을 해석하지 않고 그대로 저장했다가
        # 이후 API 요청 헤더에 Bearer 토큰으로 전달만 한다.
        token = (result or {}).get("access_token", "")
        if not token:
            raise RuntimeError("로그인 응답에 access_token 이 없습니다.")

        team_app.save_auth_token(token)
        team_app.save_auth_username(username)
        self.current_user = result.get("user")
        self.accept()
