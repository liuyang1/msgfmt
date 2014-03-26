#! -*- encoding=utf8 -*-
import sys
import os
import string
import time


def transDateVmg(date):
    # decode time format
    return time.strptime(date, "%I:%M%p, %Y %b %d")


# TODO:
# rewrite this parse function
def loadvmg(fn):
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


# iter walk vmg file
def walkDir(path):
    vmglst = []
    for f in os.listdir(path):
        f = os.path.abspath(os.path.join(path, f))
        if os.path.isdir(f):
            vmglst.extend(walkDir(f))
        elif os.path.isfile(f):
            vmglst.append(loadvmg(f))
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
    print "%s inputdir [outputdir=.]" % (name)
    sys.exit()


if __name__ == "__main__":
    if len(sys.argv) == 2:
        outdir = "."
    elif len(sys.argv) == 3:
        outdir = sys.argv[2]
    else:
        usage(sys.argv[0])
    print "walk dir ", sys.argv[1]
    msg = walkDir(sys.argv[1])
    print "outputTimeline to ", outdir
    outputTimeline(msg, outdir)
