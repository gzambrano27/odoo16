# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP - Spanish number to text script
#    Based on original OpenERP /tools/amount_to_text.py
#    Copyright (C) 2012 KM Sistemas de informaciÃ³n, S.L. All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
#-------------------------------------------------------------
#SPANISH
#-------------------------------------------------------------

units_29 = ( 'CERO', 'UN', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS',
          'SIETE', 'OCHO', 'NUEVE', 'DIEZ', 'ONCE', 'DOCE',
          'TRECE', 'CATORCE', 'QUINCE', 'DIECISÃ‰IS', 'DIECISIETE', 'DIECIOCHO',
          'DIECINUEVE', 'VEINTE', 'VEINTIÃƒÂšN', 'VEINTIDÃ“S', 'VEINTITRÃ‰S', 'VEINTICUATRO',
          'VEINTICINCO', 'VEINTISÃ‰IS', 'VEINTISIETE', 'VEINTIOCHO', 'VEINTINUEVE' )       

tens = ( 'TREINTA', 'CUARENTA', 'CINCUENTA', 'SESENTA', 'SETENTA', 'OCHENTA', 'NOVENTA', 'CIEN')       

denom = ('',
          'MIL', 'MILLÃ“N', 'MIL MILLONES', 'BILLÃ“N', 'MIL BILLONES', 'TRILLÃ“N', 'MIL TRILLONES',
          'CUATRILLÃ“N', 'MIL CUATRILLONES', 'QUINTILLÃ“N', 'MIL QUINTILLONES', 'SEXTILLÃ“N', 'MIL SEXTILLONES', 'SEPTILLÃ“N',
          'MIL SEPTILLONES', 'OCTILLÃ“N', 'MIL OCTILLONES', 'NONILLÃ“N', 'MIL NONILLONES', 'DECILLÃ“N', 'MIL DECILLONES' )

denom_plural = ('',
          'MIL', 'MILLONES', 'MIL MILLONES', 'BILLONES', 'MIL BILLONES', 'TRILLONES', 'MIL TRILLONES',
          'CUATRILLONES', 'MIL CUATRILLONES', 'QUINTILLONES', 'MIL QUINTILLONES', 'SEXTILLONES', 'MIL SEXTILLONES', 'SEPTILLONES',
          'MIL SEPTILLONES', 'OCTILLONES', 'MIL OCTILLONES', 'NONILLONES', 'MIL NONILLONES', 'DECILLONES', 'MIL DECILLONES' )

# convertir valores inferiores a 100 a texto espaÃ‘ol.
def _convert_nn(val):
    if val < 30:
        return units_29[val]
    for (dcap, dval) in ((k, 30 + (10 * v)) for (v, k) in enumerate(tens)):
        if dval + 10 > val:
            if val % 10:
                return dcap + ' Y ' + units_29[val % 10]
            return dcap

# convertir valores inferiores a 1000 a texto espaÃ‘ol.
def _convert_nnn(val):
    word = ''
    (mod, quotient) = (val % 100, val // 100)
    if quotient > 0:
        if quotient == 1:
            if mod == 0:
                word = 'CIEN'
            else:
                word = 'CIENTO'
        elif quotient == 5:
                word = 'QUINIENTOS'
        elif quotient == 9:
            word = 'NOVECIENTOS'
        else:
            word = units_29[quotient] + 'CIENTOS'
        if mod > 0:
            word = word + ' '
    if mod > 0:
        word = word + _convert_nn(mod)
    return word

def spanish_number(val):
    if val < 100:
        return _convert_nn(val)
    if val < 1000:
        return _convert_nnn(val)
    #valores a partir de mil
    for (didx, dval) in ((v - 1, 1000 ** v) for v in range(len(denom))):
        if dval > val:
            mod = 1000 ** didx
            l = val // mod
            r = val - (l * mod)
            
            # Varios casos especiales:
            # Si l==1 y didx==1 (caso concreto del "mil"), no queremos que diga "un mil", sino "mil".
            # Si se trata de un millÃƒÂ³n y ÃƒÂ³rdenes superiores (didx>0), sÃƒÂ­ queremos el "un".
            # Si l > 1 no queremos que diga "cinco millÃƒÂ³n", sino "cinco millones".
            if l == 1: 
                if didx == 1:
                    ret = denom[didx]
                else:
                    ret = _convert_nnn(l) + ' ' + denom[didx]
            else:        
                ret = _convert_nnn(l) + ' ' + denom_plural[didx]
         
            if r > 0:
                ret = ret + ' ' + spanish_number(r)
            return ret

def amount_to_text_es(number, currency,join_sep=' CON ',with_zero=False):
    number = '%.2f' % number
    # Nota: el nombre de la moneda viene dado en el informe como "euro". AquÃƒÂ­ se convierte a
    # uppercase y se pone en plural aÃ‘adiendo una "s" al final del nombre. Esto no cubre todas
    # las posibilidades (nombres compuestos de moneda), pero sirve para las mÃƒÂ¡s comunes.
    units_name = currency.upper()
    int_part, dec_part = str(number).split('.')       
    start_word = spanish_number(int(int_part))
    end_word = spanish_number(int(dec_part))
    cents_number = int(dec_part)
    cents_name = (cents_number > 1) and 'CÃ‰NTIMOS' or 'CÃ‰NTIMO'
    final_result = start_word +' ' + units_name
    
    # AÃ‘adimos la "s" de plural al nombre de la moneda si la parte entera NO es UN euro
    if int(int_part) != 1:
        final_result += 'S'
    
    if not with_zero:
        if int(dec_part) > 0:
            final_result += join_sep + end_word +' '+cents_name
    else:
        final_result += join_sep + end_word +' '+cents_name
    return final_result


#-------------------------------------------------------------
# Generic functions
#-------------------------------------------------------------

def amount_to_text_ec(number, currency,join_sep=' CON ',with_zero=False):
    number = '%.2f' % number
    units_name = currency.upper()
    int_part, dec_part = str(number).split('.')       
    start_word = spanish_number(int(int_part))
    cents_number = int(dec_part)
    final_result = start_word +' '
    if int(int_part) != 1:
        units_name += ((currency.__len__()>1) and "ES" or '')
        units_name=" "+units_name
#     if int(dec_part) > 0:
#         final_result += join_sep + str(int(dec_part)) +'/100'        
    if not with_zero:
        if int(dec_part) > 0:
            final_result += join_sep + str(int(dec_part)) +'/100'
    else:
        final_result += join_sep + str(int(dec_part)) +'/100'      
    return final_result+ units_name

_translate_funcs = {'es' : amount_to_text_es,
                    'ec' : amount_to_text_ec}

def amount_to_text(nbr, lang='es', currency='euros'):
    """
    Converts an integer to its textual representation, using the language set in the context if any.
    Example:
        1654: thousands six cent cinquante-quatre.
    """
    if not _translate_funcs.has_key(lang):
        print("WARNING: no translation function found for lang: '%s'" % (lang,))
        lang = 'es'
    return _translate_funcs[lang](abs(nbr), currency)