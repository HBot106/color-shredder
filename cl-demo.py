import pyopencl as cl
import numpy as np

# create an OpenCL context
ctx = cl.create_some_context()
queue = cl.CommandQueue(ctx)

# create the kernel input
a = np.array(np.arange(10), dtype=np.int32)

# kernel output placeholder
b = np.empty(a.shape, dtype=np.int32)

# create context buffers for a and b arrays
# for a (input), we need to specify that this buffer should be populated from a
a_dev = cl.Buffer(ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR,
                    hostbuf=a)
# for b (output), we just allocate an empty buffer
b_dev = cl.Buffer(ctx, cl.mem_flags.WRITE_ONLY, b.nbytes)

# OpenCL kernel code
code = """
__kernel void test1(__global int* a, __global int* b) {
    int i = get_global_id(0);
    b[i] = a[i]*a[i];
}
"""

# compile the kernel
prg = cl.Program(ctx, code).build()

# launch the kernel
event = prg.test1(queue, a.shape, None, a_dev, b_dev)
event.wait()

# copy the output from the context to the Python process
cl.enqueue_copy(queue, b, b_dev)

# if everything went fine, b should contain squares of integers
print(b)