#!/bin/bash
#set -x # Echo commands to stderr

ACTION=$1
DEVICE=$2
UPLOAD_SPEED=$3
DOWNLOAD_SPEED=$4
PORT=$5
PROTOCOL=$6
IFB="ifb0"

stop() {
    sudo tc qdisc del dev $DEVICE root 2>/dev/null
    sudo tc qdisc del dev $DEVICE ingress 2>/dev/null
    sudo tc qdisc del dev $IFB root 2>/dev/null
    sudo modprobe -r ifb 2>/dev/null
}

start() {
    stop

    # --- Ingress (Download) Shaping ---
    sudo modprobe ifb numifbs=1
    sudo ip link set dev $IFB up

    sudo tc qdisc add dev $DEVICE handle ffff: ingress
    sudo tc filter add dev $DEVICE parent ffff: protocol all u32 match u32 0 0 action mirred egress redirect dev $IFB

    sudo tc qdisc add dev $IFB root handle 1: htb
    sudo tc class add dev $IFB parent 1: classid 1:1 htb rate ${DOWNLOAD_SPEED}kbit burst 15k

    # --- Egress (Upload) Shaping ---
    sudo tc qdisc add dev $DEVICE root handle 2: htb
    sudo tc class add dev $DEVICE parent 2: classid 2:1 htb rate ${UPLOAD_SPEED}kbit burst 15k


    # --- Filter creation ---
    if [ -n "$PORT" ]; then
        add_filters_for_protocol() {
            local proto_num=$1
            local proto_name=$2 # For logging/debug purposes if needed

            if [[ $PORT == *-* ]] ; then
                local start_port=$(echo $PORT | cut -d'-' -f1)
                local end_port=$(echo $PORT | cut -d'-' -f2)
                for ((port=$start_port; port<=$end_port; port++)); do
                    sudo tc filter add dev $IFB parent 1:0 protocol ip u32 match ip protocol $proto_num 0xff match ip sport $port 0xffff flowid 1:1
                    sudo tc filter add dev $DEVICE parent 2:0 protocol ip u32 match ip protocol $proto_num 0xff match ip dport $port 0xffff flowid 2:1
                done
            else
                sudo tc filter add dev $IFB parent 1:0 protocol ip u32 match ip protocol $proto_num 0xff match ip sport $PORT 0xffff flowid 1:1
                sudo tc filter add dev $DEVICE parent 2:0 protocol ip u32 match ip protocol $proto_num 0xff match ip dport $PORT 0xffff flowid 2:1
            fi
        }

        if [ "$PROTOCOL" = "TCP" ]; then
            add_filters_for_protocol 6 "TCP"
        elif [ "$PROTOCOL" = "UDP" ]; then
            add_filters_for_protocol 17 "UDP"
        elif [ "$PROTOCOL" = "Both" ]; then
            add_filters_for_protocol 6 "TCP"
            add_filters_for_protocol 17 "UDP"
        fi
    else
        # Shape all traffic
        sudo tc filter add dev $IFB parent 1:0 protocol all u32 match u32 0 0 flowid 1:1
        sudo tc filter add dev $DEVICE parent 2:0 protocol all u32 match u32 0 0 flowid 2:1
    fi
    # --- Print Status ---
    #echo "--- TC Status after applying rules ---"
    #echo "--- Qdiscs on $DEVICE ---"
    #tc -s qdisc show dev $DEVICE
    #echo "--- Classes on $DEVICE ---"
    #tc -s class show dev $DEVICE
    #echo "--- Qdiscs on $IFB ---"
    #tc -s qdisc show dev $IFB
    #echo "--- Classes on $IFB ---"
    #tc -s class show dev $IFB
}

if [ "$ACTION" = "start" ]; then
    start
elif [ "$ACTION" = "stop" ]; then
    stop
fi
