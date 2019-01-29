import os
import re
import time
import subprocess
from kubernetes import client, config, utils


def create_deployment():
    k8s_client = client.ApiClient()
    os.chdir('/home/vijayj')
    k8s_api = utils.create_from_yaml(k8s_client, "the_deployment.yaml")
    deps = k8s_api.read_namespaced_deployment("fio-deployment", "default")
    print("Deployment {0} created".format(deps.metadata.name))


def get_pod_name():
    v1 = client.CoreV1Api()
    ret = v1.list_pod_for_all_namespaces()

    for i in ret.items:
        if "fio-deployment" in i.metadata.name:
            print('Pod Status: ', i.status.phase)
            status = i.status.phase
            while status != 'Running':
                time.sleep(15)
                status = check_pod_status(i.metadata.name)
                print('Pod Status: ', status)
            return i.metadata.name


def check_pod_status(pod_name):
    v1 = client.CoreV1Api()
    ret = v1.list_pod_for_all_namespaces()
    for i in ret.items:
        if i.metadata.name == pod_name:
            return i.status.phase


def get_pod_logs(size, exec_time):
    pod_name = get_pod_name()
    print('PodName: ', pod_name)
    logs = str(subprocess.getoutput('kubectl logs {0}'.format(pod_name)))

    while 'aggrb=' not in logs:
        time.sleep(15)
        logs = str(subprocess.getoutput('kubectl logs {0}'.format(pod_name)))

    with open('Logs_Pod_write{}_{}sec.txt'.format(size, exec_time), 'w') as wf:
        wf.write(logs)


def get_stats(logs):

    io = re.findall('io=([0-9]+)KB', logs)[0]
    aggrb = re.findall('aggrb=([0-9]+)KB/s', logs)[0]
    perf_tuple = (io, aggrb)

    return perf_tuple


def fio_outside(size, exec_time):
    cmd = 'fio --name=randwrite --ioengine=libaio --iodepth=5 --rw=randwrite --bs=1k --direct=0 --size=100M --numjobs=1 --runtime=120 --group_reporting'
    cmd = cmd.replace('--size=100M', '--size={0}'.format(size))
    cmd = cmd.replace('--runtime=120', '--runtime={0}'.format(exec_time))
    logs = subprocess.getoutput(cmd)

    with open('Logs_Local_write{}_{}sec.txt'.format(size, exec_time), 'w') as wf:
        wf.write(logs)


def create_yaml_file(mem_size, run_time):
    os.chdir('/home/vijayj')
    k = open('fio-deployment.yaml')
    j = k.read()
    j = j.replace('--size=??', '--size={0}'.format(mem_size))
    j = j.replace('--runtime=??', '--runtime={0}'.format(run_time))
    k.close()
    new = open('the_deployment.yaml', 'w')
    new.write(j)
    new.close()


def delete_deployment():
    subprocess.getoutput('kubectl delete deployment fio-deployment')


if __name__ == '__main__':
    config.load_kube_config()
    data_list = [('5G', '600'), ('10G', '600'), ('50G', '1200'), ('100G', '1200')]
    # data_list = [('100G', '1200')]

    for data in data_list:
        create_yaml_file(data[0], data[1])
        create_deployment()
        time.sleep(40)
        get_pod_logs(data[0], data[1])
        fio_outside(data[0], data[1])
        delete_deployment()
        time.sleep(40)

   
