"""
Test script for multi-pass adaptive chunking.

Tests chunking behavior with different document structures:
1. Proper markdown headers
2. One H1 with bold subheadings
3. One H1 with structural markers
4. One H1 with no structure
"""

import sys
from pathlib import Path

# Add parent directory to path to import chunker
sys.path.insert(0, str(Path(__file__).parent))

from chunker import MarkdownChunker


def test_proper_headers():
    """Test document with proper markdown headers."""
    print("\n" + "=" * 70)
    print("TEST 1: Proper Markdown Headers")
    print("=" * 70)

    markdown = """# Course Syllabus

## Course Description
This course covers fundamental concepts in computer science including algorithms, data structures, and software design.

## Learning Objectives
By the end of this course, students will be able to:
- Design efficient algorithms
- Implement data structures
- Write clean, maintainable code

## Assessment
The course will be evaluated through assignments, quizzes, and a final project."""

    chunker = MarkdownChunker(max_tokens=500, overlap_tokens=50)
    chunks = chunker.chunk(markdown)

    print(f"Total chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        metadata = chunk["metadata"]
        print(f"\n--- Chunk {i+1} ({len(chunk['content'])} chars) ---")
        print(f"Method: {metadata.get('chunking_method', 'unknown')}")
        print(f"Heading: {metadata.get('heading', 'N/A')}")
        print(f"Content preview: {chunk['content'][:100]}...")

    return chunks


def test_bold_headings():
    """Test document with one H1 and bold subheadings."""
    print("\n" + "=" * 70)
    print("TEST 2: One H1 with Bold Subheadings")
    print("=" * 70)

    # Make document longer to exceed token limits
    markdown = """# Study Guide

**Algorithms and Complexity**
This section covers fundamental algorithms including sorting, searching, and graph algorithms. Students will learn to analyze time and space complexity. Sorting algorithms include bubble sort, merge sort, quicksort, and heapsort. Each has different time complexity characteristics. Searching algorithms include linear search, binary search, and hash-based lookups. Graph algorithms cover breadth-first search, depth-first search, Dijkstra's algorithm, and minimum spanning trees. Understanding these fundamentals is essential for any computer science student.

**Data Structures**
Understanding data structures is crucial for efficient programming. Topics include arrays, linked lists, trees, and hash tables. Arrays provide constant-time access but have fixed size. Linked lists allow dynamic sizing but require linear-time access. Trees enable hierarchical data organization and logarithmic-time operations for balanced trees. Hash tables offer average constant-time lookups but require careful handling of collisions. Students will implement each data structure from scratch and analyze their performance characteristics.

**Software Design Principles**
Good software design involves modularity, abstraction, and encapsulation. These principles help create maintainable and scalable systems. Modularity allows code to be broken into independent components. Abstraction hides implementation details behind interfaces. Encapsulation bundles data with the methods that operate on that data. Other principles include separation of concerns, single responsibility, and DRY (don't repeat yourself). These patterns are applicable across all programming paradigms."""

    chunker = MarkdownChunker(max_tokens=300, overlap_tokens=50)
    chunks = chunker.chunk(markdown)

    print(f"Total chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        metadata = chunk["metadata"]
        print(f"\n--- Chunk {i+1} ({len(chunk['content'])} chars) ---")
        print(f"Method: {metadata.get('chunking_method', 'unknown')}")
        print(f"Heading: {metadata.get('heading', 'N/A')}")
        print(f"Content preview: {chunk['content'][:100]}...")

    return chunks


def test_structural_markers():
    """Test document with one H1 and structural markers."""
    print("\n" + "=" * 70)
    print("TEST 3: One H1 with Structural Markers")
    print("=" * 70)

    # Make document longer to trigger splitting
    markdown = """# Course Notes

- Lecture 1: Introduction to Computer Science
  Covering the history of computing, basic concepts, and career opportunities in the field. We'll explore how computers work from hardware to software layers. Topics include binary representation, von Neumann architecture, and the evolution of computing devices from room-sized machines to smartphones. Students will also learn about various career paths including software engineering, data science, cybersecurity, and AI research.

- Lecture 2: Programming Fundamentals
  Variables, control structures, functions, and basic data types in modern programming languages. This lecture introduces programming concepts that apply across languages. We'll cover variables and types, conditionals and loops, functions and parameters, arrays and collections. Students will write their first programs and understand basic algorithms. Debugging techniques and version control will also be introduced as essential skills for professional development.

- Lecture 3: Data Structures
  Arrays, linked lists, stacks, queues, and trees with practical examples. Data structures are fundamental to efficient algorithms. We'll implement each structure from scratch and analyze their time and space complexity. Students will learn when to use each data structure and understand trade-offs between them. Memory management and pointer concepts will also be covered for those using languages with manual memory control.

1. Assignment: Hello World Program - Simple introduction to programming basics
2. Assignment: Calculator with multiple operations - Practice with control structures
3. Assignment: Todo List application - Learn arrays and data manipulation
4. Assignment: Binary Search implementation - Demonstrate divide and conquer approach"""

    chunker = MarkdownChunker(max_tokens=250, overlap_tokens=50)
    chunks = chunker.chunk(markdown)

    print(f"Total chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        metadata = chunk["metadata"]
        print(f"\n--- Chunk {i+1} ({len(chunk['content'])} chars) ---")
        print(f"Method: {metadata.get('chunking_method', 'unknown')}")
        print(f"Heading: {metadata.get('heading', 'N/A')}")
        print(f"Content preview: {chunk['content'][:100]}...")

    return chunks


def test_no_structure():
    """Test document with one H1 and no structure."""
    print("\n" + "=" * 70)
    print("TEST 4: One H1 with No Structure (Fallback to Paragraph Splitting)")
    print("=" * 70)

    # Make document longer to force paragraph splitting with increased overlap
    markdown = """# Unstructured Document

This is a document without any clear structure. It contains a lot of text but no headings, bold text, or structural markers. The text just flows in paragraphs without any organization. This type of document is challenging to chunk semantically because there are no natural boundaries. The chunking algorithm will need to rely on paragraph boundaries and sentence splitting to create chunks. Each paragraph might cover multiple topics. This makes it harder for semantic search to find relevant information.

However, increased overlap between chunks will help maintain context across chunk boundaries. When we can't detect semantic boundaries like headers or list items, we preserve context by overlapping chunks. This means that information at the end of one chunk will be repeated at the beginning of the next chunk. This helps the semantic search maintain continuity and find relevant information even when it spans multiple chunks.

Let's add more text to make this long enough to require multiple chunks. The algorithm should split this into multiple chunks while trying to maintain some context through overlapping content. Overlapping chunks are especially important for unstructured text where topics might transition without clear markers. The increased overlap (100 tokens instead of 50) provides more context but at the cost of more redundant text across chunks.

This paragraph adds more content to ensure we exceed the token limit and trigger the fallback mechanism. The fallback is the final safety net when all other detection methods fail. It splits by paragraphs and sentences while respecting token limits, and adds increased overlap between chunks to maintain context since no semantic structure was found."""

    chunker = MarkdownChunker(max_tokens=200, overlap_tokens=50)
    chunks = chunker.chunk(markdown)

    print(f"Total chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        metadata = chunk["metadata"]
        print(f"\n--- Chunk {i+1} ({len(chunk['content'])} chars) ---")
        print(f"Method: {metadata.get('chunking_method', 'unknown')}")
        print(f"Heading: {metadata.get('heading', 'N/A')}")
        print(f"Content preview: {chunk['content'][:100]}...")

    return chunks


def test_large_section_with_bold():
    """Test large section that exceeds token limit with bold headings."""
    print("\n" + "=" * 70)
    print("TEST 5: Large Section with Bold Headings (Requires Splitting)")
    print("=" * 70)

    # Create a longer document to exceed token limits
    markdown = """# Course Materials

**Introduction to Computer Science**
Computer science is the study of computation, information, and automation. It spans theoretical disciplines such as algorithms, theory of computation, and information theory to practical disciplines including the design and implementation of hardware and software. Computer science is no more about computers than astronomy is about telescopes. It is the study of computation, not specifically computers. As such, several attributes that characterize computer science as an academic discipline distinguish it from other disciplines like mathematics, physics, and engineering.

**Fundamental Algorithms**
An algorithm is a finite sequence of well-defined instructions, typically used to solve a class of specific problems or to perform a computation. Algorithms are fundamental to computer science and are used as specifications for performing calculations, data processing, automated reasoning, and other tasks. In contrast to a heuristic algorithm, an algorithm is guaranteed to terminate after a finite number of steps. Different algorithms may complete the same task with a different set of instructions in more or less time, space, or effort than others.

**Data Structures**
A data structure is a data organization, management, and storage format that enables efficient access and modification. More precisely, a data structure is a collection of data values, the relationships among them, and the functions or operations that can be applied to the data. Data structures serve as the basis for abstract data types (ADT). The ADT defines the logical form of the data type, while the data structure implements the physical form of the data type.

**Complexity Analysis**
Algorithmic analysis is important to the theoretical computer science because it allows for the comparison of algorithms independent of a particular hardware platform or programming language implementation. For example, an algorithm that takes n steps to complete a task may be considered to be more efficient than an algorithm that takes n² steps to complete the same task, regardless of which computer each algorithm is run on. Complexity analysis thus provides a way to characterize the efficiency of algorithms in a way that is independent of the hardware used to run them.

**Software Engineering**
Software engineering is the systematic application of engineering approaches to the development of software. Software engineering deals with the organizing and analyzing software to get the best from them. It does not deal with the actual production of the software. It's a sub-discipline of systems engineering, information systems, and information technology. Software engineering is a direct sub-field of engineering and has an overlap with computer science and management science."""

    chunker = MarkdownChunker(max_tokens=200, overlap_tokens=50)  # Lower max_tokens to force splitting
    chunks = chunker.chunk(markdown)

    print(f"Total chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        metadata = chunk["metadata"]
        print(f"\n--- Chunk {i+1} ({len(chunk['content'])} chars) ---")
        print(f"Method: {metadata.get('chunking_method', 'unknown')}")
        print(f"Heading: {metadata.get('heading', 'N/A')}")
        print(f"Content preview: {chunk['content'][:100]}...")

    return chunks


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("MULTI-PASS ADAPTIVE CHUNKING TEST SUITE")
    print("=" * 70)

    try:
        test_proper_headers()
        test_bold_headings()
        test_structural_markers()
        test_no_structure()
        test_large_section_with_bold()

        print("\n" + "=" * 70)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 70)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
