#! -*- encoding=utf8 -*-
import sys
import os
import string
import time


def loadvmg(fn):
    def transDateVmg(date):
        # decode time format
        return time.strptime(date, "%I:%M%p, %Y %b %d")
    with open(fn) as fp:
        fromname, toname = "", ""
        content = ""
        for line in fp.readlines():
            line = line.strip()
            if len(line) > 0 and line[0].isupper():
                pos = string.find(line, ':')
                k = line[0:pos]
                v = line[pos + 1:]
                if k == 'FN;CHARSET=UTF-8':
                    if fromname == '':
                        fromname = v
                    else:
                        toname = v
                elif k == 'Date':
                    date = transDateVmg(v)
                else:
                    pass
            else:
                content = line
    return (date, fromname, toname, content)


def loadvmg2(fn):
    vmsg = ("BEGIN:VMSG", "END:VMSG")
    venv = ("BEGIN:VENV", "END:VENV")
    vcard = ("BEGIN:VCARD", "END:VCARD")
    vbody = ("BEGIN:VBODY", "END:VBODY")

    def transDateVmg(date):
        return time.strptime(date, "%I:%M%p, %Y %b %d")

    def extract(s, headtail):
        head, tail = headtail[0], headtail[1]
        begin = s.index(head)
        offset = begin + len(head)
        cnt = 1
        while 1:
            idx0 = s.find(head, offset)
            idx1 = s.find(tail, offset)
# 找到开始符号与结束符号,并且开始符号较小,这样,还需要再找到一个结束符号
            if idx0 != -1 and idx1 != -1 and idx0 < idx1:
                offset = idx1 + len(tail)
# 只找到结束符号,或者
# 找到开始符号与结束符号,并且开始符号较大,则可以结束
            elif (idx0 == -1 and idx1 != -1) or (idx0 != -1 and idx1 != -1 and idx0 > idx1):
                end = idx1
                break
            else:
                print idx0, idx1
                raise ValueError
        return s[begin + len(head): end].strip()

    def parseKV(cnt):
        cnt = cnt.strip()
        cnt = [line.split(":") for line in cnt.split("\n")]
        return {v[0]: v[1].strip() for v in cnt}

    def parseVmsg(cnt):
        cnt = extract(cnt, vmsg)
        d = {}
        card = extract(cnt, vcard)
        env = extract(cnt, venv)
        d.update(parseKV(cnt[:cnt.index("BEGIN")]))
        d["card"] = parseVcard(card)
        d["env"] = parseVenv(env)
        return d

    def parseVcard(cnt):
        return parseKV(cnt)

    def parseVenv(cnt):
        card = extract(cnt, vcard)
        env = extract(cnt, venv)
        d = {}
        d["card"] = parseVcard(card)
        d["env"] = parseVenv2(env)
        return d

    def parseVenv2(cnt):
        d = {}
        d["body"] = parseVbody(extract(cnt, vbody))
        return d

    def parseVbody(cnt):
        d = {}
        try:
            date = extract(cnt, ("Date:", "\n"))
            linepos = cnt.index('\n')
            d["text"] = cnt[linepos + 1:]
        except ValueError:
# 处理空短信的异常情况
            date = cnt[cnt.index("Date:")+len("Date:"):]
            d["text"] = ""
        d["date"] = transDateVmg(date)
        return d
    fp = open(fn)
    content = fp.read()
    fp.close()
    d = parseVmsg(content)
# 处理没有存储号码对应的名字的异常问题
    try:
        fromname = d["card"]["FN;CHARSET=UTF-8"]
    except KeyError:
        fromname = d["card"]["FN"]
    try:
        toname = d["env"]["card"]["FN;CHARSET=UTF-8"]
    except KeyError:
        toname = d["env"]["card"]["FN"]
    ret = (d["env"]["env"]["body"]["date"],
           fromname, toname,
           d["env"]["env"]["body"]["text"])
    return ret


def loadcsv(fn):
    def transdate(date):
        if len(date) == 0:
            date = "1900.01.01 00:00"
        return time.strptime(date, "%Y.%m.%d %H:%M")
    fp = open(fn)
    smslst = []
    for line in fp.readlines():
        line = line.strip()
        line = line.split(',')
        if len(line) <= 2:
            continue
        if line[1] == "submit":  # send
            fromname = "me"
            toname = line[3][1:-1]
        elif line[1] == "deliver":  # receive
            fromname = line[2][1:-1]
            toname = "me"
        else:
            continue
        date = transdate(line[5][1:-1])
        content = line[7][1:-1]
        smslst.append((date, fromname, toname, content))
    return smslst


def loadSMS(fn):
    _, fntype = os.path.splitext(fn)
    if fntype == ".vmg":
        return [loadvmg2(fn)]
    elif fntype == ".csv":
        return loadcsv(fn)
    else:
        return None


# iter walk vmg file
def walkDir(path):
    vmglst = []
    for f in os.listdir(path):
        f = os.path.abspath(os.path.join(path, f))
        if os.path.isdir(f):
            vmglst.extend(walkDir(f))
        elif os.path.isfile(f):
            ret = loadSMS(f)
            if ret:
                vmglst.extend(ret)
        else:
            pass
    return vmglst


def splitConversation(vmglst):
    ret = {}
    for vmg in vmglst:
        k1 = vmg[1], vmg[2]
        k2 = vmg[2], vmg[1]
        if k1 in ret.keys():
            ret[k1].append(vmg)
        elif k2 in ret.keys():
            ret[k2].append(vmg)
        else:
            ret[k1] = [vmg]
    return ret


def outputTimeline(vmglst, outdir="."):
    vmgdict = splitConversation(vmglst)
    for k, vmglst in vmgdict.iteritems():
        vmglst = sorted(vmglst, key=lambda x: x[0])
        fn = outdir + "/%s-%s.sms" % (k[0], k[1])
        fp = open(fn, "w")
        for vmg in vmglst:
            date = time.strftime("%Y-%m-%d %H:%M", vmg[0])
            fp.write("%s %s %s %s\r\n" % (date, vmg[1], vmg[2], vmg[3]))
        fp.close()


def usage(name):
    print "%s [inputdir=.] [outputdir=.]" % (name)
    print "\tsupport VMG, CSV format"
    sys.exit()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        indir, outdir = ".", "."
    elif len(sys.argv) == 2:
        indir, outdir = sys.argv[1], "."
    elif len(sys.argv) == 3:
        indir, outdir = sys.argv[1], sys.argv[2]
    else:
        usage(sys.argv[0])
    print "walk dir ", indir
    msg = walkDir(indir)
    print "outputTimeline to ", outdir
    outputTimeline(msg, outdir)
