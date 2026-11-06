from src.managers.file_manager import FileManager


def test_root_initialization():
    fm = FileManager()
    fm.configure({"default_owner": "root"})
    assert fm.root is not None
    assert fm.root.name == "/"
    assert fm.root.is_dir is True


def test_create_directory():
    fm = FileManager()
    fm.configure({"default_owner": "root"})
    success, msg = fm.create_directory("/documents")
    assert success is True
    assert "documents" in fm.root.children


def test_create_and_read_file():
    fm = FileManager()
    fm.configure({"default_owner": "root"})
    # Create the directory in memory first
    fm.create_directory("/docs")
    success, msg = fm.create_file("/docs/notes.txt", content="hello world")
    assert success is True

    # Read it back from memory
    read_success, content = fm.read_file("/docs/notes.txt")
    assert read_success is True
    assert content == "hello world"


def test_duplicate_file_fails():
    fm = FileManager()
    fm.configure({"default_owner": "root"})
    fm.create_file("/data.csv")
    success, msg = fm.create_file("/data.csv")
    assert success is False
    assert "already exists" in msg


def test_read_missing_file_fails():
    fm = FileManager()
    fm.configure({"default_owner": "root"})
    success, msg = fm.read_file("/missing.txt")
    assert success is False
    assert "not found" in msg