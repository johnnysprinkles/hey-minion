from bs4 import BeautifulSoup
import requests

def files(**kwargs):
    """Transforms the kwargs to a structure suitable for passing as "files"
    to a requests call, for multipart/form-data. Values should all be strings.
    """
    # The "None" makes it omit the filename part.
    return {key: (None, value) for key, value in kwargs.items()}

class HeySession:
    WEB_SOCKET_URL = 'wss://app.hey.com/cable'
    USER_AGENT = 'Hey Minion/1.0'
    ORIGIN = 'https://app.hey.com'

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({'user-agent': self.USER_AGENT})

    def get(self, path):
        return self._session.get(f'{self.ORIGIN}{path}')

    def get_unscreened_senders(self):
        """Sadly, https://app.hey.com/clearances.json doesn't contain the senders only how many
        are pending, so we're stuck with fragile HTML parsing.
        """
        response = self.get('/clearances')
        html = BeautifulSoup(response.content, 'html.parser')
        senders = set()
        for h3 in html.find_all('h3', class_='clearance__sender'):
            spans = h3.find_all('span')
            senders.add(spans[0].text + ' ' + spans[1].text.strip())
        return senders

    def get_channels(self):
        """Returns a list of JSON strings (not dictionaries)"""
        response = self.get('/')
        soup = BeautifulSoup(response.content, 'html.parser')

        channels = []
        for tag in soup.find_all('meta', {'data-controller': 'page-update-subscription'}):
            channels.append(tag['data-page-update-subscription-channel-value'])
        return channels

    def sign_in(self, email, password):
        """When successful this sets updated versions of some cookies:
        * authenticity_token
        * _haystack_session cookie"""
        return self._session.post(f'{self.ORIGIN}/sign_in',
            files=files(email_address=email, password=password))

    def respond_to_challenge(self, code, csrf):
        return self._session.post(
            f'{self.ORIGIN}/two_factor_authentication/challenge',
            headers = {'X-CSRF-Token': csrf},
            files = files(code=code, scheme_type='totp'))

    def get_cookie(self):
        """Returns a cookie header string"""
        cookies = [f'{name}={value}' for name, value in self._session.cookies.get_dict().items()]
        return '; '.join(cookies)

    def get_cookies(self):
        """Returns a string to string dictionary"""
        return self._session.cookies.get_dict()

    def apply_cookies(self, cookie_dict):
        requests.utils.add_dict_to_cookiejar(self._session.cookies, cookie_dict)        
