import secrets
import string


class PasswordGenerator:
    def __init__(self):
        self.default_length = 16
        self.use_uppercase = True
        self.use_lowercase = True
        self.use_digits = True
        self.use_symbols = True
        self.exclude_ambiguous = True

    def generate(self, length=None, uppercase=None, lowercase=None,
                 digits=None, symbols=None, exclude_ambiguous=None):

        if length is None:
            length = self.default_length

        if length < 4:
            length = 4
        if length > 64:
            length = 64

        use_upper = uppercase if uppercase is not None else self.use_uppercase
        use_lower = lowercase if lowercase is not None else self.use_lowercase
        use_digits = digits if digits is not None else self.use_digits
        use_symbols = symbols if symbols is not None else self.use_symbols
        excl_amb = exclude_ambiguous if exclude_ambiguous is not None else self.exclude_ambiguous

        upper = string.ascii_uppercase
        lower = string.ascii_lowercase
        digits_set = string.digits
        symbols_set = "!@#$%^&*()_+-=[]{}|;:,.<>?"

        if excl_amb:
            upper = upper.replace('I', '').replace('O', '')
            lower = lower.replace('l', '')
            digits_set = digits_set.replace('0', '').replace('1', '')

        chars = ""
        if use_upper:
            chars += upper
        if use_lower:
            chars += lower
        if use_digits:
            chars += digits_set
        if use_symbols:
            chars += symbols_set

        if not chars:
            chars = lower + digits_set

        password = []

        if use_upper:
            password.append(secrets.choice(upper))
        if use_lower:
            password.append(secrets.choice(lower))
        if use_digits:
            password.append(secrets.choice(digits_set))
        if use_symbols:
            password.append(secrets.choice(symbols_set))

        remaining = length - len(password)
        for _ in range(remaining):
            password.append(secrets.choice(chars))

        for i in range(len(password)):
            j = secrets.randbelow(len(password))
            password[i], password[j] = password[j], password[i]

        return ''.join(password)

    def generate_memorable(self, words=4, separator='-'):
        """Генерация запоминаемого пароля из слов"""
        word_list = ['apple', 'banana', 'cherry', 'dragon', 'eagle', 'forest',
                     'garden', 'happy', 'island', 'jungle', 'knight', 'lion',
                     'mountain', 'night', 'ocean', 'peace', 'queen', 'river',
                     'storm', 'thunder', 'unity', 'victory', 'water', 'xenon',
                     'yellow', 'zenith']

        words_list = [secrets.choice(word_list) for _ in range(words)]
        password = separator.join(words_list)

        password += str(secrets.randbelow(100))

        return password