import re
import xbmc
from babelfish import Language, Country

# https://github.com/xbmc/translations/tree/master/translations/xbmc-main/merged-langfiles/language
EXCEPTIONS = {
    'Chinese (Simple)': 'zh-Hans',
    'Chinese (Traditional)': 'zh-Hant',
    'Hindi (Devanagiri)': 'hi-IN',
    'Persian (Iran)': 'fa-IR',
    'Serbian (Cyrillic)': 'sr-Cyrl'
}

ALPHA2_EXCEPTIONS = {
    'pt-BR': 'pb'
}


class LanguageConverter(object):

    def from_english(self, language):
        if language in EXCEPTIONS:
            return Language.fromietf(EXCEPTIONS[language])

        language_match = re.search('(\w[\w\s]*\w)', language)
        if not language_match:
            return

        language_english = language_match.group(1)
        language_alpha3 = xbmc.convertLanguage(language_english, format=xbmc.ISO_639_2)
        if not language_alpha3:
            return

        result = Language.fromcode(language_alpha3, 'alpha3b')
        result.country = self.get_country(language)
        return result

    def to_alpha2(self, language):
        code = str(language)

        return ALPHA2_EXCEPTIONS.get(code, code)

    def get_country(self, language):
        country_match = re.search('\s*\((\w[\w\s]*\w)\)', language)
        if not country_match:
            return

        country_code = country_match.group(1)

        return Country(country_code) if len(country_code) == 2 else Country.fromcode(country_code, converter='name')
