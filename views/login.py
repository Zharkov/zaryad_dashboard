import html

_LOGIN_PAGE = """<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8">
<title>ЗАРЯД · Вход</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/static/style.css">
</head><body>
<div class="login-wrap">
  <div class="login-box">
    <div class="login-logo">
      <svg width="100" height="46" viewBox="0 0 80 36">
        <rect x="2" y="6" width="68" height="24" rx="3" fill="none" stroke="#ffd60a" stroke-width="2.5"/>
        <rect x="71" y="12" width="6" height="12" rx="1.5" fill="#ffd60a"/>
        <rect x="5" y="9" width="62" height="18" rx="1.5" fill="rgba(255, 214, 10, 0.08)"/>
        <text x="36" y="22" text-anchor="middle" fill="#ffd60a" font-family="Arial" font-size="11" font-weight="800" letter-spacing="1.5">ЗАРЯД</text>
      </svg>
      <div>
        <div class="name">ЗАРЯД</div>
        <div class="sub" style="text-align:center;">Табель учёта</div>
      </div>
    </div>
    {error_html}
    <form class="login-form" method="POST" action="/login">
      <label>Логин</label>
      <input type="text" name="username" autocomplete="username" autofocus required>
      <label>Пароль</label>
      <input type="password" name="password" autocomplete="current-password" required>
      <div class="remember">
        <input type="checkbox" name="remember" id="rem" value="1" checked>
        <label for="rem" style="margin:0; text-transform:none; letter-spacing:0;">Запомнить на 30 дней</label>
      </div>
      <button type="submit">Войти</button>
    </form>
  </div>
</div>
</body></html>
"""


def render_login(error: str | None = None) -> str:
    err = ""
    if error:
        err = f'<div class="login-error">{html.escape(error)}</div>'
    return _LOGIN_PAGE.format(error_html=err)
