import os
from transitions import Machine
from transitions.extensions import GraphMachine

class FilenameInOut:
    def __init__(self, name_in, ext_in=None, dir_out=None, ext_out=None):
        self.name = name_in
        self.ext_in = ext_in
        self.filenames = []
        try:
            if os.path.isdir(name_in):
                if not self.ext_in:
                    raise Exception('ext_in not specified')
                else:
                    self.filenames = [f.replace(self.ext_in, '') for f in os.listdir(name_in) if f.endswith(self.ext_in)]
                self.path_in = name_in
            else:
                (file_head, self.ext_in) = os.path.splitext(name_in)
                (self.path_in, filename) = os.path.split(file_head)
                self.filenames.append(filename)
        except Exception as e:
            raise e
        except:
            raise NameError('"{0}" is not a valid file/dir name'.format(name_in))

        self.ext_out = ext_out if ext_out else self.ext_in

        if dir_out:
            self.path_out = dir_out
            os.makedirs(self.path_out, exist_ok=True) 
        else:
            self.path_out = self.path_in


    def get_in_names(self):
        return [os.path.join(self.path_in, f) + self.ext_in for f in self.filenames]

    def get_out_names(self):
        return [os.path.join(self.path_out, f) + self.ext_out for f in self.filenames]
    
    @property
    def file_names(self):
        return self.filenames
    
    @property
    def out_path(self):
        return self.path_out

def flatten(x):
    result = []
    for el in x:
        if hasattr(el, "__iter__") and not isinstance(el, str):
            result.extend(flatten(el))
        else:
            result.append(el)
    return result

class MdParagraphId(object):
    states = ['outside', 'chap_title', 'chap', 'sec_title', 'sec']
    transitions = [
        ['step_in', 'outside', 'chap_title'],
        ['chap_title_to_content', 'chap_title', 'chap'],
        ['chap_instant_to_sec', 'chap_title', 'sec_title'],
        ['chap_to_sec', 'chap', 'sec_title'],
        ['chap_content_to_title', 'chap', 'chap_title'],
        ['sec_title_to_content', 'sec_title', 'sec'],
        ['sec_content_to_title', 'sec', 'sec_title'],
        ['sec_content_to_chap', 'sec', 'chap_title'],
        ['sec_instant_to_chap', 'sec_title', 'chap_title'],
    ]

    def __init__(self, name):
        self._name = name
        self.reset()

        # self.m = Machine(model=self, states=MdParagraph.states, transitions=MdParagraph.transitions, initial='outside')
        self._machine = GraphMachine(model=self,
                                states=MdParagraphId.states,
                                # transitions=MdParagraphId.transitions,
                                initial=MdParagraphId.states[0],
                                auto_transitions=False,
                                send_event=True,
                                show_conditions=True,
                                show_state_attributes=True)
        self._machine.add_transition('to_content', 'outside', '=')
        self._machine.add_transition('to_content', ['sec', 'sec_title'], 'sec', after=self.change_index)
        self._machine.add_transition('to_content', ['chap', 'chap_title'], 'chap', after=self.change_index)
        # self._machine.add_transition('to_title', 'outside', 'chap_title', conditions=[self.is_chap_title], after=self.reset_to_title)
        # self._machine.add_transition('to_title', 'chap_title', '=', conditions=[self.is_chap_title], after=self.reset_to_title)
        # self._machine.add_transition('to_title', 'chap_title', 'sec_title', conditions=[self.is_sec_title], after=self.reset_to_title)
        # self._machine.add_transition('to_title', 'sec_title', '=', conditions=[self.is_sec_title], after=self.reset_to_title)
        # self._machine.add_transition('to_title', 'sec_title', 'chap_title', conditions=[self.is_chap_title], after=self.reset_to_title)
        # self._machine.add_transition('to_title', 'chap', 'chap_title', conditions=[self.is_chap_title], after=self.reset_to_title)
        # self._machine.add_transition('to_title', 'chap', 'sec_title', conditions=[self.is_sec_title], after=self.reset_to_title)
        # self._machine.add_transition('to_title', 'sec', 'chap_title', conditions=[self.is_chap_title], after=self.reset_to_title)
        # self._machine.add_transition('to_title', 'sec', 'sec_title', conditions=[self.is_sec_title], after=self.reset_to_title)
        self._machine.add_transition('to_title',
                                    ['outside', 'chap_title', 'sec_title', 'chap', 'sec', ],
                                    'chap_title',
                                    conditions=[self.is_chap_title],
                                    after=self.reset_to_title)
        self._machine.add_transition('to_title',
                                    ['chap_title', 'sec_title', 'chap', 'sec'],
                                    'sec_title',
                                    conditions=[self.is_sec_title],
                                    after=self.reset_to_title)
        self._machine.get_graph().draw('state_diagram.png', prog='dot')
        self._machine.add_transition('reset', '*', 'outside', after=self.reset)


    def reset(self):
        self._line = ''
        self._chap_name = ''
        self._sec_name = ''
        self._chap_index = 0
        self._sec_index = 0

    def change_index(self, event):
        if self.state == 'chap':
            self._chap_index += 1
        elif self.state == 'sec':
            self._sec_index += 1

    def reset_to_title(self, event):
        name = event.kwargs.get('name', '')
        self._sec_index = 0
        self._chap_index = 0
        if self.state == 'chap_title':
            self._chap_name = name
        if self.state == 'sec_title':
            self._sec_name = name

    def is_chap_title(self, event):
        return self._line.startswith('# ')

    def is_sec_title(self, event):
        return self._line.startswith('## ')

    def proc_line(self, line):
        self._line = line
        if self._line.startswith('#'):
            name = (' '.join(line.split(' ')[1:])).replace(' ', '_')
            self.to_title(name=name)
        else:
            self.to_content()

    @property
    def tag(self):
        if self._chap_name and self._sec_name and self._sec_index > 0:
            return '{0}-{1}-{2}'.format(self._chap_name, self._sec_name, self._sec_index)
        elif self._chap_name and self._chap_index > 0:
            return '{0}-{1}'.format(self._chap_name, self._chap_index)
        else:
            return ''

    @property
    def id(self):
        if self._chap_index > 0:
            return self._chap_index
        elif self._sec_index > 0:
            return self._sec_index
        else:
            return None

class MdIdAttacher(object):
    def __init__(self, file_or_str):
        if os.path.isfile(file_or_str):
            with open(file_or_str, 'r') as f:
                content = f.read()
        else:
            content = file_or_str
        
        self._paragraphs = content.split('\n\n')
        self._id_generator = MdParagraphId('bogey')
        self._ids = []
        self._tags = []
        self._attached = []

    def _gen_ids(self):
        for p in self._paragraphs:
            self._id_generator.proc_line(p)
            self._ids.append(self._id_generator.id)
            self._tags.append(self._id_generator.tag)
    
    @property
    def ids(self):
        if not self._ids:
            self._gen_ids()
        return self._ids

    @property
    def tags(self):
        if not self._tags:
            self._gen_ids()
        return self._tags

    def attach(self, only_tags=True):
        temp = zip(self.ids, self.tags, self._paragraphs)
        res = ''
        if only_tags:
            res = '\n\n'.join(['[]{{#{0}}}\n{1}'.format(tag, p) if id else p for (id, tag, p) in temp])
        else:
            res = '\n\n'.join(['{0}. []{{#{1}}}\n{2}'.format(id, tag, p) if id else p for (id, tag, p) in temp])
        return res

    @property
    def attached_full(self):
        return self.attach(False)

    @property
    def attached(self):
        return self.attach()
