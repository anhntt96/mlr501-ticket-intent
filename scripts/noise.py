"""Hàm tạo biến thể tiếng Việt không chuẩn (bỏ dấu, teencode, gõ Telex, trộn tiếng Anh)
và khoá phát hiện câu trùng. Dùng chung cho các script dựng dữ liệu.
"""
import re
import string
import unicodedata

VARIANTS = ["clean", "no_diacritics", "teencode", "telex", "code_switch", "mixed"]


def strip_diacritics(text):
    """Bỏ dấu: 'Hủy đơn' -> 'Huy don'."""
    text = text.replace("đ", "d").replace("Đ", "D")
    nfd = unicodedata.normalize("NFD", text)
    return unicodedata.normalize("NFC", "".join(c for c in nfd if unicodedata.category(c) != "Mn"))


# Viết tắt/teencode phổ biến khi chat (cụm dài đặt trước).
TEENCODE = [
    ("không", "ko"), ("được", "dc"), ("với", "vs"), ("gì", "j"), ("vậy", "v"),
    ("rồi", "r"), ("biết", "bít"), ("tài khoản", "tk"), ("thanh toán", "tt"),
    ("nhân viên", "nv"), ("bạn", "b"), ("mình", "mk"), ("chưa", "chưa"),
    ("tôi", "e"), ("giúp", "giúp"), ("thế nào", "ntn"), ("như thế nào", "ntn"),
    ("làm sao", "lm sao"), ("làm", "lm"), ("muốn", "mún"), ("trước", "trc"),
]
# Trộn tiếng Anh: thuật ngữ khách Việt hay dùng nguyên tiếng Anh.
CODE_SWITCH = [
    ("hoàn tiền", "refund"), ("bồi hoàn", "refund"), ("hủy", "cancel"), ("huỷ", "cancel"),
    ("đơn hàng", "order"), ("đơn", "order"), ("địa chỉ", "address"),
    ("tài khoản", "account"), ("mật khẩu", "password"), ("mã PIN", "PIN"),
    ("thanh toán", "payment"), ("kiểm tra", "check"), ("theo dõi", "track"),
    ("nhân viên thật", "agent"), ("nhân viên", "admin"), ("khiếu nại", "complain"),
    ("giao hàng", "ship"),
]


def replace_words(text, pairs, rng=None, prob=1.0):
    out = text
    for src, dst in sorted(pairs, key=lambda p: -len(p[0])):
        pat = re.compile(r"(?<!\w)" + re.escape(src) + r"(?!\w)", re.IGNORECASE)
        out = pat.sub(lambda m: dst if (rng is None or rng.random() < prob) else m.group(0), out)
    return out


def casual(text):
    """Viết thường, bỏ dấu câu cuối như khi chat."""
    return text.lower().rstrip(" ?.!")


def teencode(text, rng):
    return casual(replace_words(text, TEENCODE, rng, prob=0.8))


def code_switch(text, rng):
    return replace_words(text, CODE_SWITCH, rng, prob=0.7)


TONE_KEY = {"́": "s", "̀": "f", "̉": "r", "̃": "x", "̣": "j"}


def word_to_telex(word):
    """Gõ Telex mà quên bật bộ gõ: 'hủy' -> 'huyr', 'đơn' -> 'ddown'."""
    out, tone = [], ""
    for ch in word:
        if ch in "đĐ":
            out.append("dd")
            continue
        base, *marks = unicodedata.normalize("NFD", ch)
        piece = base
        for m in marks:
            if m == "̂":
                piece = base + base           # â ê ô -> aa ee oo
            elif m in ("̆", "̛"):
                piece = base + "w"            # ă ơ ư -> aw ow uw
            elif m in TONE_KEY:
                tone = TONE_KEY[m]
        out.append(piece)
    return "".join(out) + tone


def telex_typo(text, rng, max_words=2):
    words = text.split(" ")
    idx = [i for i, w in enumerate(words) if strip_diacritics(w) != w]
    for i in rng.sample(idx, min(max_words, len(idx))):
        words[i] = word_to_telex(words[i].lower())
    return " ".join(words)


def mixed(text, rng):
    """Nhiễu nặng kiểu ticket thật: trộn tiếng Anh + teencode + bỏ dấu."""
    return strip_diacritics(teencode(code_switch(text, rng), rng))


# Khoá để phát hiện câu trùng (bỏ dấu câu, hoa/thường, khoảng trắng thừa).
def group_key(template):
    t = template.lower().translate(str.maketrans("", "", string.punctuation))
    return " ".join(t.split())
