import re
import time
from winevt import EventLog

import mmap
import contextlib

from Evtx.Evtx import FileHeader
from Evtx.Views import evtx_file_xml_view

match_code = {'4624': '已成功登录的账户', '4625': '账户登录失败', '4634': '账户被注销'}
match_login = {'0':'未知登录[0]','2':' 本地交互登录[2]','3':'网络登录[3]','4':'计划任务[4]','5':'服务[5]','6':'代理[6]','7':'解除屏幕锁定[7]','8':'网络明文登录[8]','9':'新身份登录[9]','10':'远程登录[10]','11':'缓存登录[11]'}
html_head = '''
<!DOCTYPE html>
<html lang="en">

<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>Document</title>
	<style>
		* {
			margin: 0;
			padding: 0;
			box-sizing: border-box;
		}

		*:focus {
			outline: none;
		}

		#wrap {
			padding-top: 2rem;
		}

		.type {
			margin-left: 2rem;
			border: 1px solid #d7d7d7;
			padding: 1rem;
			margin: 1rem;
			overflow: hidden;
		}

		.title {
			font-size: .85rem;
			font-weight: 600;
			pointer-events: none;
			margin-left: 2rem
		}

		p {
			line-height: 2rem;
			cursor: pointer
		}

		#btn {
			position: fixed;
			bottom: 10px;
			right: 10px;
			background: #000;
			padding: 10px;
			transform: scale(.8);
			cursor: pointer
		}

	</style>
</head>

<body>
	<div id="wrap"></div>
	<span id='btn' style="display: none">
		<svg width="39px" height="41px">
			<path fill-rule="evenodd" fill="rgb(255, 255, 255)" d="M38.541,20.686 C37.947,21.267 36.984,21.267 36.391,20.686 L20.743,5.367 L20.761,38.727 C20.761,39.975 20.082,40.986 19.242,40.985 C18.403,40.984 17.723,39.971 17.722,38.723 L17.704,5.540 L2.591,20.358 C1.998,20.940 1.037,20.940 0.444,20.358 C-0.149,19.777 -0.149,18.834 0.444,18.253 L17.621,1.411 C17.752,1.283 17.905,1.194 18.063,1.123 C18.341,0.629 18.754,0.309 19.221,0.310 C19.753,0.311 20.220,0.719 20.491,1.335 C20.801,1.378 21.099,1.505 21.337,1.738 L38.541,18.580 C39.135,19.162 39.135,20.104 38.541,20.686 Z" />
		</svg>
	</span>
</body>
<script>
var json = 
'''

html_foot = '''
	function print() {
		console.log(...arguments)
	}

	function info(s, obj) {
		print(s);
		s = s.split('|');
		for (let i of s) {
			obj = obj[i]
		}
		return obj
	}

	function changeStyle(tags, state) {
		for (let i = 1; i < tags.children.length; i++) {
			tags.childNodes[i].style.display = state
		}
	}

	function addTag(value, place, obj = json) {
		if (place.childElementCount > 1) return;
		let v = value ? info(value, obj) : obj;
		let isJump = false
		for (let i in v) {
			if (i === 'value') {
				for (let j of v[i]) {
					let p = document.createElement('p');
					p.innerHTML = j
					p.setAttribute('class', 'title')
					place.appendChild(p)
				}
				continue
			}
			if (isJump) {
				isJump = !isJump
				continue
			}
			let div = document.createElement('div'),
				p = document.createElement('p');
			if (blackList.indexOf(v[i]) > -1) // || i === 'Time'
				isJump = !isJump
			if (typeof(v[i]) === 'string' || typeof(v[i]) === 'number') {
				p.innerHTML = i + ':' + v[i];
				div.setAttribute('class', 'title')
			} else {
				p.setAttribute('data-value', value === undefined ? i : value + '|' + i);
				div.setAttribute('class', 'type');
				p.innerHTML = i
			}
			div.appendChild(p);
			place.appendChild(div)
		}
	}

	function events(value, place) {
		addTag(value, place);
		let content = document.getElementsByTagName('p');
		for (let i = 0; i < content.length; i++) {
			content[i].onclick = function(e) {
				window.event ? window.event.cancelBubble = true : e.stopPropagation;
				if (i in onoff && onoff[i]) {
					onoff[i] = !onoff[i];
					changeStyle(this.parentNode, 'none');
					return
				}
				events(this.getAttribute('data-value'), this.parentNode);
				changeStyle(this.parentNode, 'block');
				onoff[i] = true
			}
		}
	}

	//style//
	btn.onclick = function smoothscroll() {
		let currentScroll = document.documentElement.scrollTop || document.body.scrollTop;
		if (currentScroll > 0) {
			window.requestAnimationFrame(smoothscroll);
			window.scrollTo(0, currentScroll - (currentScroll / 10));
		}
	}

	window.onscroll = function() {
		if (wrap.getBoundingClientRect().top < -document.documentElement.clientWidth / 2)
			btn.style.display = 'block'
		else
			btn.style.display = 'none';
	}

	let onoff = {};
	let blackList = ['computer', "IP address", 'eventID']
	wrap.innerHTML = '<p class="title">时间范围：从 ' + timeList[0] + ' 到 ' + timeList[1] + '</p>'
	events(undefined, wrap)

</script>

</html>
'''
time_list = ['']

def matchevents(i, tag, event_end=1):
    try:
        if event_end:
            x = re.search('<.*?%s.*?>(.*?)</' % (tag), i).group(1)
        else:
            x = re.search("<.*?%s.*?[\"'](.*?)[\"'].*?>" % tag, i).group(1)
        return x if x != "" else 'Null'
    except:
        return "Null"


def judge(obj, num, s, v):
    value = s[num]
    num += 1
    if num < len(s) + 1:
        if value in obj:
            obj['num'] += 1
        else:
            obj['name'] = v[num - 1]
            obj['num'] = obj['num'] + 1 if len(obj) > 1 else 1
            if num == len(s):
                if 'value' in obj:
                    obj['value'].append(value)
                else:
                    obj['value'] = [value]
                return obj
            else:
                obj[value] = {}
        judge(obj[value], num, s, v)
    return obj

def analyze(i,final_count):
    event_id = matchevents(i, 'EventID')
    if event_id in match_code:
        global_type = {
            "computer": matchevents(i, 'Computer').replace('_', '.'),
            "logonType": match_login[matchevents(i, "LogonType")],
            "eventID": match_code[event_id],
            "IP address": matchevents(i, "IpAddress"),
            "Time": matchevents(i, "TimeCreated",0)[:19].replace('T', ' ')
        }

        if len(time_list) == 1:
            time_list[0] = global_type['Time']
            time_list.append('')
        else:
            time_list[1] = global_type['Time']
        types = []
        keys = []
        for key, val in global_type.items():
            keys.append(key)
            types.append(val)

        return judge(final_count, 0, types, keys)
    return final_count


def main():
    final_count = {}
    evt = input('[1]获取系统安全日志\n[2]获取evtx日志文件\n')
    if evt == "1":
        try:
            query = EventLog.Query("Security", "Event/EventData/Data[@Name='LogonType']")
            print('<----------start---------->')
            for event in query:
                i = event.xml
                final_count = analyze(i,final_count)
        except:
            input('请以管理员的方式打开，按回车键退出')
            return
    elif evt == "2":
        EvtxPath = input('[*]请输入文件路径:')
        with open(EvtxPath, 'r') as f:
            with contextlib.closing(mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)) as buf:
                print('<----------start---------->')
                fh = FileHeader(buf, 0)
                for xml, record in evtx_file_xml_view(fh):
                    final_count = analyze(xml,final_count)

    file = 'log{}.html'.format(''.join([str(x) for x in time.localtime(int(time.time()))]))
    with open(file, 'w', encoding='utf-8') as f:
        f.write(html_head + str(final_count) + "\nlet timeList=" + str(time_list) + html_foot)
    print(file + "已保存")
    input('按回车键退出')


if __name__ == '__main__':
    main()
