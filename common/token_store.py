import time

token_temp = {}


class TokenStore(object):
    def __init__(self, key):
        """
        key is used to distinguish different Store
        :param key:
        """
        self.key = key

    def save(self, token, expires_in, create_time=None):
        """
        save token
        :param token: token
        :param expires_in: how long the token is valid, unit is second
        :param create_time: if create_time is None, use current time
        :return:
        """
        current_time = time.time()
        token_temp[self.key] = {
            'token': token,
            'expires_in': expires_in,
            'update_time': current_time,
            'create_time': create_time or current_time
        }

    def get(self):
        """
        if token is expires, clear it and return None
        :return:
        """
        if self.key in token_temp:
            token = token_temp[self.key]
            if time.time() - token['update_time'] > token['expires_in']:
                token_temp.pop(self.key)
                return None
            return token['token']
        return None

    def refresh(self, expires_in):
        """
        refresh token if it exists
        :param expires_in: how long the token is valid, unit is second
        :return:
        """
        if self.key in token_temp:
            token_dict = token_temp[self.key]
            self.save(token_dict['token'], expires_in, token_dict['create_time'])

    @staticmethod
    def clean(key):
        """
        clean token by key
        :param key: string
        :return:
        """
        if key in token_temp:
            token_temp.pop(key)

    @staticmethod
    def clean_all():
        """
        clean all token
        :return: 
        """
        for key in token_temp:
            token_temp.pop(key)
