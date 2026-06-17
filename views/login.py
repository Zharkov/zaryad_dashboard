import html

from views.common import COMMON_CSS

_LOGIN_PAGE = """<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8">
<title>ЗАРЯД · Вход</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
{css}
.login-wrap {{ min-height: 100vh; display: flex; align-items: center;
              justify-content: center; padding: 16px; }}
.login-box {{ background: var(--surf); padding: 32px; border-radius: 12px;
             border: 1px solid var(--border); width: 100%; max-width: 380px;
             box-shadow: 0 8px 32px rgba(0,0,0,0.4); }}
.login-logo {{ display: flex; flex-direction: column; align-items: center;
              gap: 12px; margin-bottom: 28px; }}
.login-logo .name {{ font-size: 28px; font-weight: 800; letter-spacing: 2px;
                    color: var(--brand); }}
.login-logo .sub {{ font-size: 11px; color: var(--muted);
                    text-transform: uppercase; letter-spacing: 2px; }}
.login-form label {{ display: block; font-size: 12px; color: var(--muted);
                     text-transform: uppercase; letter-spacing: 1px;
                     margin: 12px 0 6px; font-weight: 600; }}
.login-form input {{ width: 100%; padding: 12px 14px; background: var(--bg);
                     border: 1px solid var(--border); border-radius: 8px;
                     color: var(--text); font-size: 15px; font-family: inherit; }}
.login-form input:focus {{ outline: none; border-color: var(--brand); }}
.login-form .remember {{ display: flex; align-items: center; gap: 8px;
                          margin: 18px 0; font-size: 13px; color: var(--muted); }}
.login-form .remember input {{ width: auto; accent-color: var(--brand); }}
.login-form button {{ width: 100%; padding: 12px; background: var(--brand);
                       color: #000; border: none; border-radius: 8px;
                       font-size: 15px; font-weight: 700; cursor: pointer;
                       margin-top: 8px; font-family: inherit; }}
.login-form button:hover {{ background: #ffe44d; }}
.login-error {{ background: rgba(248, 81, 73, 0.1); border: 1px solid rgba(248, 81, 73, 0.3);
               color: var(--bad); padding: 10px 14px; border-radius: 6px;
               font-size: 13px; margin-bottom: 16px; }}
</style>
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
    return _LOGIN_PAGE.format(css=COMMON_CSS, error_html=err)
