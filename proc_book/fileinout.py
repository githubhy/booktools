import os

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
