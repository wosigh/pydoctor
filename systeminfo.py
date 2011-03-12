import subprocess

def systeminfo():
    p = subprocess.Popen(['systeminfo','/FO','CSV'],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    data = p.communicate()[0].split('\r\n')
    keys = data[0][1:-1].split('","')
    values = data[1][1:-1].split('","')
    result = {}
    for i in range(len(keys)):
        result[keys[i]] = values[i]
    return result
